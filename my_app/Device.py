
from LabJackPython import Close
from time import sleep
from Port import Port
from sampling import retry
import u3
import statistics
import os
import pickle
import logging
logger = logging.getLogger(__name__)

#may need a way to prevent repeats of the same device. 
class Device():
    all = []

    def __init__(self, name, sn):
        self.name = name
        self.sn = sn
        self.ports = [Port(self, x) for x in range(1,17)]
        Device.all.append(self)

    def __eq__(self, other) -> bool:
        return (self.name == other.name and self.sn == other.sn)
    
    @staticmethod
    def discovery():
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
            Device.all.append(Device(name, sn))
        Close()
        logger.info("Connected devices: %s", device_names)


    
  



    
