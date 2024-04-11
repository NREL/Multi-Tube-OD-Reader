
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


class Device():
    all_devices = []

    def __init__(self, name, sn):
        self.name = name
        self.sn = sn
        self.ports = [Port(self, x) for x in range(1,17)]
        Device.all_devices.append(self)
    
    @staticmethod
    def discovery(cls):
        """
        call with Device.discovery() to create Device objects for each OD reader
        staticmethods are accessible with class.method() instead of instance.method for object methods
        cls carries a call to the current class "Device"
        that way if it changes to "Devices" or "Thing" or "Hardware", we don't have to rewrite it
        """
        d = u3.openAllU3()
        device_sns= list(d.keys())
        device_names = []
        Close()
        for sn in device_sns:
            d = u3.U3(firstFound = False, serial = sn)
            name = d.getName()
            device_names.append(name)
            cls.all_devices.append(Device(name, sn))
        Close()
        logger.info("Connected devices: %s", device_names)

    @staticmethod
    def reconcile_hardware(cls, devices:list, hardware:list):
        devices = cls.load_pickle().pop(0)
        hardware = cls.discovery()
        device_attributes = set((x.id, x.name) for x in devices)
        difference = [ x for x in hardware if (x.id, x.name) not in device_attributes ]
        return devices.append(difference)
    
    @staticmethod
    @retry(max_retries = 4, wait_time = 1)
    def measure_voltage(serialNumber, ports:list, n_reps):
        d = u3.U3(firstFound = False, serial = serialNumber)
        #ports are 1-16, but the labjack refers to 0-15
        ports = [int(x) for x in ports]
        fio = sum([2**(x-1) for x in ports if x <= 8])
        eio = sum([2**(x-9) for x in ports if x >= 9])
        d.configIO(FIOAnalog = fio, EIOAnalog= eio)
        data = []
        for x in range(n_reps):
            if sleep(1/n_reps) is None:   
                data.append(d.binaryListToCalibratedAnalogVoltages(d.getFeedback([u3.AIN(PositiveChannel=int(x)-1, NegativeChannel=31, LongSettling=True, QuickSample=False) for x in ports]), isLowVoltage= True, isSingleEnded= True, isSpecialSetting= False ))
        Close()
        voltages = []
        for i,first_list in enumerate(data[0]):
            voltages.append(statistics.mean(list[i] for list in data))
        return voltages

    @staticmethod
    def load_pickle(cls, path):
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                pickle = pickle.load(f)
                return pickle
        else: 
            cls.save_pickle(path, [[],[]])
            cls.load_pickle(path)

    @staticmethod
    def save_pickle(path, object):
        """
        pickle is two lists nested inside another list
        1. list of device objects (each has it's lists of ports)
        2. list of timecourse objects
        """
        with open(path, 'wb') as f:
            pickle.dump(object, f, pickle.DEFAULT_PROTOCOL)



    
