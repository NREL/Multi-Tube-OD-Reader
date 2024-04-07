import u3
from LabJackPython import Close
import logging
import os
import pickle
from sampling import full_measurement

logger = logging.getLogger(__name__)

#save all into one pickle, maybe have a different line for each item?
# see https://stackoverflow.com/questions/20716812/saving-and-loading-multiple-objects-in-pickle-file
# will the first line be a list of device objects (with it's usage), and next line be list of experiment objects
# create a reconciler to compare usage vs experiments
# check if PID is running or not.

#build header and blanks directly to file, delete file upon cancel
#have child process only add to file, not deal with header.
#import class into child process 

#

def load_pickle(path):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            object = pickle.load(f)
            return object
    else: 
        logger.warning("pickle file not found at %s", path)

def save_pickle(path, object):
    if os.path.isfile(path):
        with open(path, 'wb') as f:
            pickle.dump(object, f, pickle.DEFAULT_PROTOCOL)
    else: 
        logger.warning("can't save to pickle file at %s", path)

def search_for_new_hardware():
    d = u3.openAllU3()
    device_sns= list(d.keys())
    Close()
    hardware = []
    local_ID = 0
    for sn in device_sns:
        d = u3.U3(firstFound = False, serial = sn)
        d.configU3(LocalID = local_ID)
        hardware.append(Device(d.getName(), sn, local_ID))
        local_ID += 1
    Close()
    logger.info("Connected devices: %s", device_sns)
    return hardware

def sort_objects(list_of_objects:list, attribute:str, reversed:bool = False):
    return list_of_objects.sort(key = lambda x: f"x.{attribute}", reverse = reversed)

def reconcile_hardware(devices:list, hardware:list):
    #preference given to device records in pickle
    #additional hardware if different from pickle
    devices = load_pickle().pop(0)
    hardware = search_for_new_hardware()
    device_attributes = set((x.id, x.name) for x in devices)
    difference = [ x for x in hardware if (x.id, x.name) not in device_attributes ]
    return devices.append(difference)

def count_available_ports(devices:list):
    return sum( d.count_available_ports() for d in devices )


# Rethink this section. Pass the actual object instead of 
def ref_ports_in_use(devices:list):
    """
    takes list of device objects
    returns list of tuples of (device object, position)
    """
    return [(d, i) for d in devices for i in d.report_ref_ports()]

def available_test_ports(devices:list):
    """
    takes list of device objects
    returns list of tuples of (device object, position)
    """
    return [(d, i) for d in devices for i in d.report_available_ports()]

def tuples_to_choices(list_of_tuples:list):
    return {(d, i):f"{d.name}:{i}" for d, i in list_of_tuples}

def regroup_tuples(tuples:list):
    set1 = set(x for x, y in tuples)
    nested_list = []
    for value in set1:
        nested_list.append([y for x, y in tuples if x is value])
    return zip(set1, nested_list)


#Maybe have port classes internal to device and timecourse classes.
class Device:
    """
    Ports in a device are Port objects. 
    Their position in the list relates to their physical position
    """
    def __init__(self, name:str, sn, local_id) -> None:
        self.name = name
        self.sn = sn
        self.local_id = local_id
        self.port_usage = tuple(self.Port() for x in range(16))

    def set_usage(self, changing_ports:list, user:str, assigned_usage:int):
        for port in changing_ports:
            self.port_usage[port-1].users.append(user)
            self.port_usage[port-1].usage = assigned_usage

    def report_available_ports(self):
        """
        returns list of unused ports
        """
        return [i+1 for i, x in enumerate(self.port_usage) if x.usage == 0]
    
    def report_ref_ports(self):
        """
        returns list of reference ports
        """
        return [i+1 for i, x in enumerate(self.port_usage) if x.usage == 2]
    
    def stop_experiment(self, experiment_name):
        for port in self.port_usage:
            if experiment_name in port.users:
                port.users.remove(experiment_name)
            if not port.users:
                port.usage = 0

    class Port:
        def __init__(self) -> None:
            self.users = []
            self.usage = 0



    
class Timecourse:
    """
    A port in a timecourse is a tuple of (device, position), unless otherwise indicated
    "ports" referes to a list of tuples
    """
    def __init__(self, name:str, interval:int, ref_port:tuple, test_ports:list) -> None:
        self.name = name
        self.interval = interval
        self.reference_port = ref_port
        self.reference_blank = None
        self.test_ports = regroup_tuples( test_ports)
        self.test_blanks = [None for x in test_ports]

        def blanks_needed(self):
            for_tests = [port for port, blank in zip(self.test_ports, self.test_blanks) if blank is None]
            for_ref = []
            if self.reference_blank is None: 
                for_ref = list(self.reference_port)
            return for_tests + for_ref
        
        def measure_blanks(self, ports_tuples:list):
            for device, ports in regroup_tuples(ports_tuples):
                for readings in full_measurement(device.sn, ports, 9):
                    for i, reading in enumerate(readings):
                        try:
                            position = self.test_ports.index( (device, ports[i]) )
                            self.test_blanks[position] = reading
                            device.set_port_usage(ports[i], self.name, 1)
                        except IndexError:
                            if (device, ports[i]) == self.reference_port:
                                self.reference_blank = reading
                                device.set_port_usage(ports[i], self.name, 2)
                            else: 
                                logger.warning('in objectify my app, the port is neither a test nor a reference port')
            
        def reset(self):
            pass
                        
                
    


        
