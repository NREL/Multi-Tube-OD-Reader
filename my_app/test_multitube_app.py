from Device import Device
from Timecourse import Timecourse
from Port import Port



def test_device_and_port_init():
    """
    if the devices is created outside of this function, it is duplicated
    this leaves 2 devices in Device.all_devices and 32 ports in Port.all_ports
    watch out for this. It may be just this script or in the app too.
    """
    d = Device("Jason", 1323401)
    d.ports[11].usage = 1
    d.ports[11].users.append("test")
    n = 8
    assert d.ports[n].position == n+1
    assert type(d.ports[0]) == Port
    assert d.ports[6].device is d
    assert d.ports[6].device.ports[2].device is d #that's cool!
    assert type(Port.all_ports) is list
    assert d.ports[n] in Port.all_ports
    assert d.ports[1].usage == 0
    assert d.ports[9].users == []
    assert d.ports[11].usage == 1
    assert d.ports[11].users == ["test"]
    assert len(Port.all_ports) == 16
    assert len(Device.all_devices) == 1
    assert [p for p in Port.all_ports if p.usage == 1] == [d.ports[11]]

def test_port_methods():
    """
    Don't make new d, call it from the class variable. 
    It passes from one method to another, saved in the Class itself
    """
    d = Device.all_devices[0] 
    n = 3
    assert len(Device.all_devices) == 1
    assert d.ports[n].position == n+1
    assert len(Port.all_ports) == 16
    assert len(Device.all_devices) == 1
    assert Port.report_available_ports() == [p for p in Port.all_ports if p.usage == 0]
    assert [p.position for p in Port.report_available_ports()] == [1,2,3,4,5,6,7,8,9,10,11,13,14,15,16]
    assert Port.count_available_ports() == 15
    assert Port.report_ref_ports() == []
    Port.remove_user("test")
    assert Port.count_available_ports() == 16
    
def test_device_methods():
    """
    these are labJack-specific and require one or more Labjacks to be connrected
    """
    pass

def test_timecourse_init():
    pass

    
if __name__ == "__main__":
    import pytest 
    pytest.main()
    