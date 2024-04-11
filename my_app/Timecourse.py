from Port import Port
from Device import Device
import math
import logging
logger = logging.getLogger(__name__)

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
    
    def read_blanks(self, ports:list):
        devices = set(p.device for p in ports)
        for device in devices:
            positions = [p.position for p in ports if p.device == device]
            readings = Device.measure_voltages(device.sn, positions, 9)
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
    
    @staticmethod
    def voltage_to_OD(v_ref_zero, time_zero_voltages, measurements):
        v_ref_now = measurements.pop(0)
        #voltage is proportional to intenisty
        #abs = -log(I/I0) =log(I0/I)
        # A-A(ref) = log(I0/I)-log(I0/I)(Ref)
        #log(A) - log(B) = log(A/B)
        return [math.log10((v_test_zero/v_test_now)/(v_ref_zero/v_ref_now)) for v_test_now, v_test_zero in zip(measurements,time_zero_voltages)]
    

    def stop_experiment(self):
        Port.remove_user(self.name)
        devices, timecourses = Device.load_pickle
        timecourses.remove(self)
        Device.save_pickle()

                