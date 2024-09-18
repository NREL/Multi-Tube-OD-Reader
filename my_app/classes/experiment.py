"""
Defines the `Experiment` class for managing and executing experiments with Multi-Tube-OD-Readers.

It includes functionality for experiment setup, execution, and data management.

Modules imported:
- classes.port: Contains the Port class for managing ports on a device.
- classes.device: Contains the Device class for managing Multi-Tube-OD-Reader devices.
- timecourse: Provides functions for measuring voltage and handling experiment configuration.
- time: Provides time-related functions.
- Path from pathlib: A class for working with filesystem paths.
- dill: Provides serialization and deserialization functions.
- logging: Provides logging functionality.
- subprocess: Provides functions for spawning new processes.
- psutil: Provides functions for process management.
"""

from classes.port import Port
from classes.device import Device
from timecourse import measure_voltage, get_config_path, append_list_to_tsv, resource_path
from time import sleep
from pathlib import Path
import dill as pickle
import logging
import subprocess
logger = logging.getLogger(__name__)
import psutil


class Experiment:
    """
    A class representing an experiment involving Multi-Tube-OD-Readers.

    Attributes:
        all (list): A class-level list of all Experiment instances.
        name (str): The name of the Experiment object and output file.
        interval (int): The time interval for the experiment.
        PID (int): The process ID of the running experiment.
        path (str): The path to the output file.
        all_ports (list): A list of Port instances involved in the experiment.
    """
    all = []
    
    def __init__(self, name:str, interval:int, test_ports:list, outfile) -> None:
        """
        Initializes an Experiment instance.

        Args:
            name (str): The name of the experiment.
            interval (int): The time interval for the experiment.
            test_ports (list): A list of Port instances used in the experiment.
            outfile (str): The path to the output file.
        """        
        self.name = name
        self.interval = interval
        self.PID = None
        self.path = outfile 
        
        #keep a list of all Port objects used in experiment.
        self.all_ports = test_ports

    def __eq__(self, other):
        """
        Defines Experiment identity based on name and PID.
        """
        return (self.name == other.name and self.PID == other.PID)
    
    def __hash__(self):
        """
        Returns a hash value for the experiment based on its name and PID.
        """
        return hash((self.name, self.PID))

    @staticmethod
    def load_pickle():
        """
        Loads the pickled configuration file.

        See add_to_pickle() in this module

        Returns:
            dict: The loaded pickled dictionary containing experiment data.
        """        
        local_pickle = {}
        
        config_file = get_config_path()

        #load file if it exists
        if config_file.is_file():
            with config_file.open('rb') as f:
                local_pickle = pickle.load(f)
        
        #write a blank file if it doesn't exist
        else: 
            local_pickle = {"Experiments":[],"Experiment_names":[]}
            Experiment.dump_config(local_pickle)

        #return current pickle, whether empty or full
        return local_pickle

    @staticmethod
    def dump_config(to_dump):
        config_file = get_config_path()
        with config_file.open('wb') as f:
            pickle.dump(to_dump, f, pickle.HIGHEST_PROTOCOL)
        
        Experiment.reconcile_pickle()

    @staticmethod
    def add_to_pickle(experiment:object = None):
        """
        Adds an Experiment object to the pickled configuration file.
        
        The pickle is two lists nested inside another list
        1. list of experiment objects (each has it's lists of ports)
        2. list of experiment names (for working with names without importing the class)
        
        Args:
            experiment (Experiment): The experiment to add to the pickle.
        """
        local_pickle = Experiment.load_pickle()
        local_pickle["Experiments"].append(experiment)
        local_pickle["Experiment_names"].append(experiment.name)
        Experiment.dump_config(local_pickle)

    @staticmethod
    def remove_from_pickle(experiment:object = None):
        """
        Removes an experiment from the pickled configuration file.

        See add_to_pickle() in this module

        Args:
            experiment (Experiment): The experiment to remove.
        """
        local_pickle = Experiment.load_pickle()
        local_pickle["Experiments"].remove(experiment)
        local_pickle["Experiment_names"].remove(experiment.name)
        Experiment.dump_config(local_pickle)

    def record_usage(self):
        """
        Marks Port objects as occupied when starting a new experiment.
        """        
        for p in self.all_ports:
            p.users.append(self.name)
            p.usage = 1

    def write_outfile_header(self):
        """
        Writes the header information to the output file.
        
        To be passed to timecourse.py
        """        
        info = ["#Info:", self.name, self.interval]
        device_names = ["#Device Names:"] + [port.device.name for port in self.all_ports]
        device_ids = ["#Device IDs:"] + [port.device.sn for port in self.all_ports]
        ports = ["#Ports:"] + [port.position for port in self.all_ports]
        usage = ["#Usage:"] + [port.usage for port in self.all_ports]
        lines = [info, device_names, device_ids, ports, usage]

        #Print Header to File
        for line in lines:
            append_list_to_tsv(line, self.path)

    def start_subproc(self):
        """
        Starts a subprocess to run the experiment script.

        Also stores PID in the Experiment object, for monitoring activity.
        """
        path_to_script = resource_path("timecourse.py")
        pickle_path = get_config_path()
        command = ["python", path_to_script, self.path, pickle_path]
        pid = subprocess.Popen(command, creationflags = subprocess.CREATE_NO_WINDOW).pid
        print("pid: ", pid)
        self.PID = pid

    def start_experiment(self):
        """
        Combines several functions to start the experiment.

        1. Writes header to output file
        2. Records usage of activated Ports
        3. Starts new timecourse.py process
        4. Updates config file with new experiment
        5. Reconciles external/internal states of Experiments vs config file
        """        
        self.write_outfile_header()
        self.record_usage()
        self.start_subproc()
        Experiment.add_to_pickle(experiment= self)
    
    def stop_experiment(self):
        """
        Stops the running experiment and removes it from the configuration file.

        Also marks Ports as available for use.

        Returns:
            str: A message indicating the result of the stop operation.
        """    
        Port.remove_user(self.name)
        Experiment.remove_from_pickle(experiment = self)
        
        #PID could die on unplanned power cycle
        #needed to protect from "PID not found" exception
        try:
            p = psutil.Process(self.PID)
            p.terminate()
            return(f"{self.name} successfully completed.")
        
        #good to tell the user their experiment was already dead
        except:
            return("Cant find the PID, it must have already stopped")
    
    @staticmethod   
    def reconcile_pickle():
        """
        Reconciles multiple sources of truth regarding the app status.

        Also reconciles duplicate objects with same identity.
        For example, memore addresses of object_1 and object_2 point to 
        two distinct (in memory) objects, but in some cases it is possible that
        object_1 __eq__ object_2 = True, based on minimal identity requirements.

        It's even more complicated because Experiments contain Ports and
        Ports contain Devices and Devices contain Ports.

        This reconciliation processes ensures that only one object exists per 
        identity, and important non-identity information is not lost by deleting duplicates. 
        """
        pickled_experiments = Experiment.load_pickle()["Experiments"]
        # selectively merge non-duplicate objects.
        # nested loops work your way down experiments, devices, objects 
        # preference given to Experiment.all list
        # list(set( [a] + [b] )) shows no preference
        # keyword "in" uses any of "==", "is", "__eq__", etc
        
        #reset Devices to only include connected
        # this doesn't delete Devices contained in 
        # existing Ports in existing Experiments
        Device.all = []
        Device.discovery()
        
        #collect form pickle any missing, non-equivalent experiments (if any)
        for e in pickled_experiments:
            if e not in Experiment.all:
                Experiment.all.append(e)

        #Iterate through known experiments
        for e in Experiment.all:
            #remove stopped experiments
            if e not in pickled_experiments:
                Experiment.all.remove(e)
                continue 
            
            #For all Ports in active Experiments
            for p in e.all_ports:
                #check for an existing equivalent device object
                if p.device not in Device.all:
                    #since this one has no equivalents, save it
                    Device.all.append(p.device)
                    continue
                
                #hold on to "is" (memory level) identical Device object
                known_device = [d for d in Device.all if d == p.device].pop(0)

                #All is well if this "is" the right device
                if known_device is p.device:
                    continue
                
                #if we've made it this far, the Device is "==" without being "is"
                #transfer existing port to the appropriate position in the Device.ports list
                known_device.ports[p.position - 1] = p

                #Assign the corrected parent Device to the Port.device variable
                p.device = known_device

        #clear and repopulate Ports list from reconciled Device list
        Port.all = []
        for d in Device.all:
            Port.all.extend(*[d.ports])