from my_app.Device import Device, Timecourse, available_test_ports


def test_add_remove_report_ports_to_device():
    device = Device("Jason", 1323401, 1)
    
    assert type(device.port_usage[0].users) == list
    device.set_usage([11, 12, 13], "new_run", 2)
    
    assert device.port_usage[10].usage==2
    assert device.port_usage[10].users==["new_run"]
    
    assert device.port_usage[11].usage==2
    assert device.port_usage[11].users==["new_run"]
    
    assert device.port_usage[12].usage==2
    assert device.port_usage[12].users==["new_run"]

    device.set_usage([11], "second_run", 2)
    assert device.port_usage[10].usage==2
    assert device.port_usage[10].users==["new_run", "second_run"]

    device.set_usage([3], "third_run", 2)
    assert device.port_usage[2].usage==2
    assert device.port_usage[2].users==["third_run"]

    device.set_usage([1, 16], "last_run", 1)
    assert len(device.report_available_ports())==len([2,4,5,6,7,8,9,10,14,15])

    assert [p.position for p in device.report_ref_ports()]==[3,11,12,13]

    device.remove_user("new_run")
    assert [p.position for p in device.report_available_ports()]==[2,4,5,6,7,8,9,10,12,13,14,15]
    assert [p.position for p in device.report_ref_ports()]==[3,11]

def test_device_timecourse_interactions():
    device = Device("Jason", 1323401, 1)
    n_ports_requested = 4
    current_run = Timecourse("bob", 1, tuple((device, 5)), available_test_ports([device])[:n_ports_requested])
    

def test_available_test_ports():
    device = Device("Jason", 1323401, 1)
    assert [p.position for p in available_test_ports([device])]==[N for N in range(1,17)]

def test_timecourse():
    device = Device("Jason", 1323401, 1)
    n_ports_requested = 4
    current_run = Timecourse("bob", 1, tuple((device, 5)), available_test_ports([device])[:n_ports_requested])
    assert current_run.test_ports==[tuple((device, N)) for N in range(1,5)]
    assert current_run.test_blanks == [None] * 4 
    assert current_run.blanks_needed()==[tuple((device, x)) for x in range(1,6)]
    #figure out how to mock the "get_measurements function"
    current_run.measure_blanks([tuple((device, N)) for N in range(1,4)])
    assert current_run.blanks_needed()==[tuple((device, N)) for N in range(4,6)]
    
if __name__ == "__main__":
    import pytest 
    pytest.main()
    