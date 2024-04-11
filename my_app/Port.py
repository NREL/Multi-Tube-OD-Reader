class Port:
    """
    Ports in a device are Port objects. 
    Their position in the list relates to their physical position
    """
    all_ports = [] #registrar

    def __init__(self, device, position) -> None:
        #register new device in registrar
        self.users = []
        self.usage = 0
        self.device = device
        self.position = position
        Port.all_ports.append(self)

    @classmethod
    def report_available_ports(cls):
        """
        returns list of unused ports
        """
        return [p for p in cls.all_ports if p.usage == 0]
    
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
        return [p for p in cls.all_ports if p.usage == 2]
    
    @classmethod
    def remove_user(cls, experiment_name):
        for p in cls.all_ports:
            if experiment_name in p.users:
                p.users.remove(experiment_name) #list remove
            if not p.users: # not [] == True
                p.usage = 0
