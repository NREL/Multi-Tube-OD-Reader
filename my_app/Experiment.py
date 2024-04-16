from Port import Port
from Device import Device
from timecourse import save_row, CONFIG_PATH
import os
import math
import pickle
import numpy as np
import logging
logger = logging.getLogger(__name__)

 
#store everything in the output file and send only the output file to the infinite loop
def load_pickle():
    local_pickle = {}
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, 'rb') as f:
            local_pickle = pickle.load(f)
    else: 
        with open(CONFIG_PATH, "wb") as f:
            local_pickle = {"Devices":[],"Experiments":[],"Experiment_names":[]}
            pickle.dump(local_pickle, f, pickle.HIGHEST_PROTOCOL)
    return local_pickle

def add_to_pickle(device:object =None, experiment:object = None):
    """
    pickle is two lists nested inside another list
    1. list of device objects (each has it's lists of ports)
    2. list of timecourse objects
    """
    local_pickle = load_pickle()
    print("local_pickle is ", local_pickle )
    if device:
        local_pickle["Devices"].append(device)
    if experiment:
        local_pickle["Experiments"].append(experiment)
        local_pickle["Experiment_names"].append(experiment.name)
    with open(CONFIG_PATH, 'wb') as f:
        pickle.dump(local_pickle, f, pickle.HIGHEST_PROTOCOL)

def remove_from_pickle(device:object = None, experiment:object = None):
    """
    pickle is two lists nested inside another list
    1. list of device objects (each has it's lists of ports)
    2. list of timecourse objects
    """
    local_pickle = load_pickle()
    if device:
        local_pickle["Devices"].remove(device)
    if experiment:
        local_pickle["Experiments"].remove(experiment)
        local_pickle["Experiment_names"].remove(experiment.name)
    with open(CONFIG_PATH, 'wb') as f:
        pickle.dump(local_pickle, f, pickle.HIGHEST_PROTOCOL)

def reconcile_pickle():
    #concatenate pickle list + other lists, 
    #make set of 
    pickle_dict = load_pickle()
    Device.discovery()
    devices = pickle_dict["Devices"] + Device.all     
    devices_as_tuples = [tuple((d.name, d.sn)) for d in devices]
    unique_devices = set(devices_as_tuples)
    
    device_indices = [devices_as_tuples.index(x) for x in unique_devices]
    devices = [devices[x] for x in device_indices]
        
    experiments = pickle_dict["Experiments"] + Experiment.all
    experiments_as_tuples = [tuple((x.name, tuple(x.test_blanks))) for x in experiments]
    unique_experiments = set(experiments_as_tuples) 

    experiment_indices = [experiments_as_tuples.index(x) for x in unique_experiments]
    experiments = [experiments[x] for x in experiment_indices]
    experiment_names = [x.name for x in experiments]


    pickle_dict = {"Devices":devices,"Experiments":experiments,"Experiment_names":experiment_names}
    with open(CONFIG_PATH, 'wb') as f:
        pickle.dump(pickle_dict, f, pickle.HIGHEST_PROTOCOL)


class Experiment:
    """

    """
    all = []
    
    def __init__(self, name:str, interval:int, ref_port, test_ports:list) -> None:
        self.name = name
        self.interval = interval
        self.reference_port = ref_port
        self.reference_blank = None
        self.test_ports = test_ports
        self.test_blanks = [None for x in test_ports]
        Experiment.all.append(self)

    def __eq__(self, other):
        return (self.name == other.name and self.interval == other.interval and self.test_blanks == other.test_blanks)
    
    def blanks_needed(self):
        for_tests = [port for port, blank in zip(self.test_ports, self.test_blanks) if blank is None]
        for_ref = []
        if self.reference_blank is None: 
            for_ref = [self.reference_port]
        return for_tests + for_ref
    
    def read_blanks(self, ports:list):
        devices = set(p.device for p in ports)
        for device in devices:
            ports_on_device = [p for p in ports if p.device == device]
            readings = Device.measure_voltages(device.sn, ports_on_device, 9)
            self.update_ports(ports_on_device, readings)

    def update_ports(self, ports:list, readings:list):
        for p, reading in zip(ports, readings):
            if p in self.test_ports:
                self.test_blanks[p.position-1]= reading
                p.users.append(self.name)
                p.usage = 1
            elif p is self.reference_port:
                self.reference_blank = reading
                p.users.append(self.name)
                p.usage = 2
            else:
                logging.warning("The blanked port is neither a reference or test port")
    
    def start_experiemnt(self):
        add_to_pickle(experiment= self)

    def stop_experiment(self):
        remove_from_pickle(experiment = self)
        Port.remove_user(self.name)
        Experiment.all.remove(self)
        

                
    
