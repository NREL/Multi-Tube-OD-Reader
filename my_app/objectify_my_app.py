import u3
from LabJackPython import Close
import logging
import os
import pickle
from sampling import full_measurement

logger = logging.getLogger(__name__)

def load_pickle(path):
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            object = pickle.load(f)
            return object
    else: 
        logger.warning("pickle file not found at %s", path)

def save_pickle(path, object):
    with open(path, 'wb') as f:
        pickle.dump(object, f, pickle.DEFAULT_PROTOCOL)

def device_discovery():
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

def reconcile_hardware(devices:list, hardware:list):
    devices = load_pickle().pop(0)
    hardware = device_discovery()
    device_attributes = set((x.id, x.name) for x in devices)
    difference = [ x for x in hardware if (x.id, x.name) not in device_attributes ]
    return devices.append(difference)

class Device:
    """
    Ports in a device are Port objects. 
    Their position in the list relates to their physical position
    """
    all_connected = [] #registrar

    def __init__(self, name:str, sn, local_id) -> None:
        #register new device in registrar
        Device.all_connected.append(self)
        self.name = name
        self.sn = sn
        self.local_id = local_id
        self.ports = []
        for x in range(1,17):
            self.Port(f"Port_{x}", x)

    @classmethod
    def report_available_ports(cls):
        """
        returns list of unused ports
        """
        unused_ports = []
        for d in cls.all_connected:
            unused_ports + [p for p in d.ports if p.usage == 0]
        return unused_ports
    
    @classmethod
    def count_available_ports(cls):
        """
        returns count of available ports
        """
        return len(cls.report_available_ports())
    
    @classmethod
    def report_ref_ports(cls):
        """
        returns list of unused ports
        """
        ref_ports = []
        for d in cls.all_connected:
            ref_ports + [p for p in d.ports if p.usage == 2]
        return ref_ports
    
    @classmethod
    def remove_user(cls, experiment_name):
        for d in cls.all_connected:
            for p in d.ports:
                if experiment_name in p.users:
                    p.users.remove(experiment_name) #list remove
                if not p.users: # not [] == True
                    p.usage = 0
    
    class Inner(object):
        pass

    def Port(self, name:str, position:int):
        device = self
        class Port(Device.Inner):
            """
            position is physical position on device
            """
            def __init__(self, name, position) -> None:
                self.users = []
                self.usage = 0
                self.position = position
                device.ports.append(self)
        return Port(name, position)

    
class Timecourse:
    """

    """
    def __init__(self, name:str, interval:int, ref_port:tuple, test_ports:list) -> None:
        self.name = name
        self.interval = interval
        self.reference_port = ref_port
        self.reference_blank = None
        self.test_ports = test_ports
        self.test_blanks = [None for x in test_ports]

    def blanks_needed(self):
        for_tests = [port for port, blank in zip(self.test_ports, self.test_blanks) if blank is None]
        for_ref = []
        if self.reference_blank is None: 
            for_ref = [self.reference_port]
        return for_tests + for_ref
    
    def get_measurements(self, device, positions, n_reps):
        #keep this separate so it can be mocked during testing
        return full_measurement(device.sn, positions, n_reps)

    def measure_blanks(self, ports:list):
        devices = [p.position for p in ports]
        readings = self.get_measurements(, positions, 9)
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
    
    def stop_experiment(self):
        Device.remove_user(self.name)
                