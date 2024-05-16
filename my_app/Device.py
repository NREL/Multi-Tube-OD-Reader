
from LabJackPython import Close
from Port import Port
from timecourse import measure_voltage
import u3
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
        devices = []
        Close()
        for sn in device_sns:
            d = u3.U3(firstFound = False, serial = sn)
            name = d.getName()
            devices.append(Device(name, sn))
        Close()
        Device.all = devices
        device_names = [d.name for d in Device.all]
        logger.info("Connected devices: %s", device_names)

    def read_calibration(self, port_objects, step, dac_set):
        """
        three-steps for readings
        give target_od = 0 for empty tube
        call again with reference tube at known OD
        """
        positions = [p.position for p in port_objects]
        voltages = measure_voltage(self.sn, positions, DAC_voltages = dac_set, n_reps=9)
        if step == 0:
            for p, v in zip(port_objects, voltages):
                p.cal0 = v
        else:
            for p, v in zip(port_objects, voltages):
                p.cal1 = v
        return voltages
    
    



    
  



    
