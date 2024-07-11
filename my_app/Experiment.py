from Port import Port
from Device import Device
from timecourse import measure_voltage, CONFIG_PATH, append_list_to_tsv, resource_path
from time import sleep
import os
import dill as pickle
import numpy as np
import logging
import subprocess
logger = logging.getLogger(__name__)
import psutil
 
#store everything in the output file and send only the output file to the infinite loop


class Experiment:
    """

    """
    all = []
    
    def __init__(self, name:str, interval:int, ref, test_ports:list, outfile) -> None:
        self.name = name
        self.interval = interval
        self.reference_port = ref
        self.reference_blank = None
        self.test_ports = test_ports
        self.test_blanks = [None for x in test_ports]
        self.PID = None
        self.path = outfile 
        self.all_ports = [self.reference_port] + self.test_ports

    def __eq__(self, other):
        return (self.name == other.name and self.PID == other.PID)
    
    def __hash__(self):
        return hash((self.name, self.PID))

    def blanks_needed(self):
        for_tests = [port for port, blank in zip(self.test_ports, self.test_blanks) if blank is None]
        for_ref = []
        if self.reference_blank is None: 
            for_ref = [self.reference_port]
        return for_tests + for_ref
    
    """    
    def read_blanks(self, ports:list):
        devices = set(p.device for p in ports)
        for device in devices:
            ports_on_device = [p for p in ports if p.device == device]
            readings = measure_voltage(device.sn, ports_on_device, 9)
            self.update_ports(ports_on_device, readings)
    """
   
    @staticmethod
    def load_pickle():
        local_pickle = {}
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, 'rb') as f:
                local_pickle = pickle.load(f)
        else: 
            with open(CONFIG_PATH, "wb") as f:
                local_pickle = {"Experiments":[],"Experiment_names":[]}
                pickle.dump(local_pickle, f, pickle.HIGHEST_PROTOCOL)
        return local_pickle

    @staticmethod
    def add_to_pickle(experiment:object = None):
        """
        pickle is two lists nested inside another list
        1. list of experiment objects (each has it's lists of ports)
        2. list of experiment names
        """
        local_pickle = Experiment.load_pickle()
        local_pickle["Experiments"].append(experiment)
        local_pickle["Experiment_names"].append(experiment.name)
        with open(CONFIG_PATH, 'wb') as f:
            pickle.dump(local_pickle, f, pickle.HIGHEST_PROTOCOL)
        Experiment.reconcile_pickle()

    @staticmethod
    def remove_from_pickle(experiment:object = None):

        local_pickle = Experiment.load_pickle()
        local_pickle["Experiments"].remove(experiment)
        local_pickle["Experiment_names"].remove(experiment.name)
        with open(CONFIG_PATH, 'wb') as f:
            pickle.dump(local_pickle, f, pickle.HIGHEST_PROTOCOL)
        Experiment.reconcile_pickle()

    @staticmethod
    def reconcile_pickle():
        """
        Used to update the inventory of connected devices and running experiments
        as kept in the pickled dictionary. 
        Device.discovery populates Device.all with all connected hardware
        """

        pickled_experiments = Experiment.load_pickle()["Experiments"]
        # selectively merge non-duplicate objects.
        # nested loops work your way down experiments, devices, objects 
        # preference given to Experiment.all list
        # list(set( [a] + [b] )) shows no preference
        # keyword "in" uses any of "==", "is", "__eq__", etc

        #collect missing, non-equivalent experiments (if any)
        for e in pickled_experiments:
            if e not in Experiment.all:
                Experiment.all.append(e)

        #remove terminated experiments (if any)
        for e in Experiment.all:
            if e not in pickled_experiments:
                Experiment.all.remove(e)
                continue #move on, done deleting old experiment
            
            for p in e.all_ports:
                if p.device not in Device.all:
                    Device.all.append(p.device)
                    continue # move on, done adding new device/port
                
                # since device is not new,
                # if it's identical move on
                known_device = [d for d in Device.all if d == p.device].pop(0)
                if known_device is p.device:
                    continue
                # since device is not identical
                # store port in known device
                # and update which device the port belongs to
                known_device.ports[p.position - 1] = p
                p.device = known_device

        Device.discovery()

        Port.all = []
        for d in Device.all:
            Port.all.extend(*[d.ports])

    def record_usage(self):
        for p in self.test_ports:
            p.users.append(self.name)
            p.usage = 1
        #Set usage/user for ref port
        self.reference_port.users.append(self.name)
        self.reference_port.usage = 2

    def write_outfile_header(self):
        device_names = ["#Device Names:"] + [port.device.name for port in self.all_ports]
        device_ids = ["#Device IDs:"] + [port.device.sn for port in self.all_ports]
        ports = ["#Ports:"] + [port.position for port in self.all_ports]
        usage = ["#Usage:"] + [port.usage for port in self.all_ports]
        calibration = ["#Reference Voltage:"] + [port.position for port in self.all_ports]
        lines = [device_names, device_ids, ports, usage, calibration]

        #Print Header to File
        append_list_to_tsv(("#Info:", self.name, self.interval), self.path)
        for line in lines:
            append_list_to_tsv(line, self.path)
        sleep(2)

    def start_subproc(self):
        path_to_script = resource_path("timecourse.py")
        command = ["python", path_to_script, self.path]
        pid = subprocess.Popen(command, creationflags = subprocess.CREATE_NO_WINDOW).pid
        print("pid: ", pid)
        #Store PID in object
        self.PID = pid

    def start_experiment(self):
        self.write_outfile_header()
        self.record_usage()
        self.start_subproc()
        Experiment.add_to_pickle(experiment= self)
    
    def stop_experiment(self):
        Port.remove_user(self.name)
        Experiment.remove_from_pickle(experiment = self)
        try:
            p = psutil.Process(self.PID)
            p.terminate()
            return(f"{self.name} successfully completed.")
        except:
            return("Cant find the PID, it must have already stopped")
