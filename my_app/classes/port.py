class Port:
    """
    Ports in a device are Port objects. 
    Their position in the list relates to their physical position
    Usage is defined as:
    0: unused
    1: used as a test
    2: used as a reference
    """
    all = [] #registrar

    def __init__(self, device, position) -> None:
        #register new device in registrar
        self.users = []
        self.usage = 0
        self.device = device
        self.position = position

    def __eq__(self, other):
        return (self.device == other.device and self.position == other.position)
    
    def __hash__(self):
        return hash((self.device, self.position, self.ODs, self.voltages, self.temperatures, self.is_calibrated))

    @classmethod
    def report_available_ports(cls):
        """
        returns list of unused ports
        """
        return [p for p in Port.all if p.usage == 0]
    
    @classmethod
    def count_available_ports(cls):
        """
        returns count of available ports
        """
        return len(Port.report_available_ports())
    
    @classmethod
    def report_ref_ports(cls):
        """
        returns list of reference ports
        """
        return [p for p in Port.all if p.usage == 2]
    
    @classmethod
    def remove_user(cls, experiment_name):
        for p in Port.all:
            if experiment_name in p.users:
                p.users.remove(experiment_name) #list remove
            if not p.users: # not [] == True
                p.usage = 0
