from sampling import full_measurement
from Port import Port
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
        Port.remove_user(self.name)
                