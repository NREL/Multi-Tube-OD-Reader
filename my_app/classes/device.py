
from LabJackPython import Close
from classes.port import Port
from timecourse import measure_voltage, retry
import u3
import time
import logging
logger = logging.getLogger(__name__)

#may need a way to prevent repeats of the same device. 
class Device():
    all = []

    def __init__(self, name, sn):
        self.name = name
        self.sn = sn
        self.ports = [Port(self, x) for x in range(1,17)]
        if self not in Device.all:
            Device.all.append(self)
        

    def __eq__(self, other) -> bool:
        return (self.sn == other.sn)
    
    def __hash__(self):
        return hash(self.sn)

    @staticmethod
    @retry(3,1)
    def discovery(reset = False):
        """
        call with Device.discovery() to create Device objects for each OD reader
        """
        #get SNs of connected devices
        d = u3.openAllU3()
        connected_sns = list(d.keys())
        Close()

        #Do we keep known/pickled devices
        if reset:
            known_devices = []
        else:
            known_devices = [d.sn for d in Device.all]

        #Only create objects for new devices
        new_devices= [sn for sn in connected_sns if sn not in known_devices]
        for sn in new_devices:
            d = u3.U3(firstFound = False, serial = sn)
            name = d.getName()
            Device(name, sn)
        Close() #close all connections

        logger.info("Connected devices: %s", [d.name for d in Device.all])
    
    def connect(self):
        d = u3.U3(firstFound = False, serial = self.sn)
        return d
    
    def rename(self, new_name):
        d = self.connect()    
        d.setName(name = new_name)
        self.name = new_name
        Close()

    def blink(self):
        d = self.connect()
        delay = 0.15 #period between flashes
        c = 0
        while c < 25:
            toggle = c % 2 
            d.getFeedback(u3.LED(State = toggle)) # for built-in LED on LabJack
            d.setDOState(16, c % 2) # for LED on CIO0
            d.getFeedback(u3.DAC8(Dac = 0, Value = d.voltageToDACBits(toggle*2.5, dacNumber= 0))) #for DAC0
            time.sleep(delay)
            c += 1
        Close()

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
    
    



    
  



    
