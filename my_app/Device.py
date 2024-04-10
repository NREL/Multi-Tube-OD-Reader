import u3
from LabJackPython import Close
from Port import Port
import os
import pickle
import logging
logger = logging.getLogger(__name__)



class Device():
    all_devices = []

    def __init__(self, name, sn):
        self.name = name
        self.sn = sn
        self.ports = [Port(self, x) for x in range(1,17)]
    
    @staticmethod 
    def discovery(cls):
        """
        call with Device.discovery() to create Device objects for each OD reader
        
        """
        d = u3.openAllU3()
        device_sns= list(d.keys())
        device_names = []
        Close()
        for sn in device_sns:
            d = u3.U3(firstFound = False, serial = sn)
            name = d.getName()
            device_names.append(name)
            cls.all_devices.append(cls(name, sn))
        Close()
        logger.info("Connected devices: %s", device_names)

    @staticmethod
    def reconcile_hardware(cls, devices:list, hardware:list):
        devices = cls.load_pickle().pop(0)
        hardware = cls.device_discovery()
        device_attributes = set((x.id, x.name) for x in devices)
        difference = [ x for x in hardware if (x.id, x.name) not in device_attributes ]
        return devices.append(difference)

    @staticmethod
    def load_pickle(cls, path):
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                object = pickle.load(f)
                return object
        else: 
            cls.save_pickle(path, [[],[]])

    @staticmethod
    def save_pickle(cls, path, object):
        with open(path, 'wb') as f:
            pickle.dump(object, f, pickle.DEFAULT_PROTOCOL)



    
