"""
Defines the `Device` class for managing and interacting with Multi-Tube-OD-Readers.

It includes functionality for device discovery, connection, renaming, and calibration.
This class and the `timecourse.py` script hand all interactions with the hardware.

A Device is the python object.
Hardware refers to the physical objects.
Python objects and hardware objects have a one-to-one relationship.

Modules imported:
- LabJackPython: Provides functionality for closing connections to LabJack devices.
- classes.port: Contains the Port class for managing ports on a Multi-Tube-OD-Reader device.
- timecourse: Contains functions for measuring voltage and retrying operations.
- u3: Provides the LabJack U3 device interface.
- time: Provides time-related functions.
- logging: Provides logging functionality.
"""

#LabJack connections are 1 per device.
# must open/close connection at each timepoint
# to allow other experiments to access the
# same Hardware between our readings
from LabJackPython import Close

from classes.port import Port
from timecourse import measure_voltage, retry
import u3
import time
import logging
logger = logging.getLogger(__name__)


class Device():
    """
    A class representing a Multi-Tube-OD-Reader device.

    Attributes:
        all (list): A class-level list of all Device instances.
        name (str): The name of the hardware.
        sn (str): The serial number of the hardware.
        ports (list): A list of Port instances associated with the hardware.
    """    
    all = []

    def __init__(self, name, sn):
        """
        Initializes a Device instance.

        Args:
            name (str): The name of the hardware.
            sn (str): The serial number of the device. Found only in device firmware.
        """        
        self.name = name
        self.sn = sn
        
        #keep a list of Port objects, representing physical ports 1 through 16
        self.ports = [Port(self, x) for x in range(1,17)]

        #keep list of all known Device objects representing connected hardware.
        if self not in Device.all:
            Device.all.append(self)
        

    def __eq__(self, other) -> bool:
        """
        Defines Device identity based serial numbers (in firmware). 
        """        
        return (self.sn == other.sn)
    
    def __hash__(self):
        """
        Returns a hash value for the device based on its serial number.
        """
        return hash(self.sn)

    @staticmethod
    @retry(3,1)
    def discovery(reset = False):
        """
        Returns a hash value for the device based on its serial number.
        
        Call with Device.discovery() to create Device objects for all Hardware

        Returns:
            int: The hash value of the device.
        """

        #get SNs of connected devices
        d = u3.openAllU3()
        connected_sns = list(d.keys())
        Close()

        #How to resolve conflict between pickled Devices (in 'config.dat') and 
        #Devices in Device.all.
        #May be inconsequential in current version.
        if reset:
            known_devices = []
        else:
            known_devices = [d.sn for d in Device.all]

        #Only create objects for new Devices
        new_devices= [sn for sn in connected_sns if sn not in known_devices]
        for sn in new_devices:
            d = u3.U3(firstFound = False, serial = sn)
            name = d.getName()
            Device(name, sn)
        Close() #close all connections to Hardware. Required to avoid conflicts.

        logger.info("Connected devices: %s", [d.name for d in Device.all])
    
    def connect(self):
        """
        Connects to the hardware using its serial number.

        Returns:
            u3.U3: The LabJack U3 device interface.
        """
        d = u3.U3(firstFound = False, serial = self.sn)
        return d
    
    def rename(self, new_name):
        """
        Renames the hardware (at a "firmware" level).

        Args:
            new_name (str): The new name for the hardware.
        """        
        d = self.connect()    
        d.setName(name = new_name)
        self.name = new_name
        Close() #close all connections to Hardware. Required to avoid conflicts.

    def blink(self):
        """
        Blinks the hardware's indicator LED for visual identification.
        """        
        d = self.connect()
        delay = 0.15 #period between flashes
        c = 0
        while c < 25:
            toggle = c % 2 
            d.getFeedback(u3.LED(State = toggle)) # for built-in LED on LabJack
            d.setDOState(16, c % 2) # for LED on CIO0, not currently implemented
            d.getFeedback(u3.DAC8(Dac = 0, Value = d.voltageToDACBits(toggle*2.5, dacNumber= 0))) #for DAC0
            time.sleep(delay)
            c += 1
        Close() #close all connections to Hardware. Required to avoid conflicts.

    
    



    
  



    
