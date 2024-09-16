class Port:
    """
    Defines Port class representing a position measure growth of a single tube in a Multi-Tube-OD-Reader.

    Attributes:
        all (list): A class-level list that holds all Port instances, serving as a registry for all ports.
        users (list): A list of experiment names using this port.
        usage (int): Indicates the current usage of the port:
            0: Unused
            1: Used as a test port
        device (Device): The Device instance to which this port belongs.
        position (int): The physical position of the port on the device (1-16 inclusive).
    """
    all = [] #registrar

    def __init__(self, device, position) -> None:
        """
        Initializes a Port instance.

        Args:
            device (Device): The Device instance to which this Port belongs.
            position (int): The physical position of the port on the device (1-16 inclusive).
        """        
        self.users = []
        self.usage = 0
        self.device = device
        self.position = position

    def __eq__(self, other):
        """
        Defines Port identity based on parent Device and Port position.
        """        
        return (self.device == other.device and self.position == other.position)
    
    def __hash__(self):
        """
        Returns a hash value for the port based on its parent Device and position.

        Returns:
            int: The hash value of the port.
        """        
        return hash((self.device, self.position))

    @classmethod
    def report_available_ports(cls):
        """
        returns list of unused ports
        """
        return [p for p in Port.all if p.usage == 0]
    
    @classmethod
    def count_available_ports(cls):
        """
        Returns a list of ports that are currently unused.
        """
        return len(Port.report_available_ports())
    
    
    @classmethod
    def remove_user(cls, experiment_name):
        """
        Removes a user (Experiment) from the list of users for each port and resets the port usage if it is no longer in use.

        Args:
            experiment_name (str): The name of the experiment to be removed from the port's users.
        """
        for p in Port.all:
            #remove experiment claiming to use the Port
            if experiment_name in p.users:
                p.users.remove(experiment_name)
            #if no one's using the Port, mark it as unused
            #not currently implemented, but useful for ports shared by experiments (such as references)
            if not p.users:
                p.usage = 0
