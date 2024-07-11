from unittest.mock import MagicMock
from Device import Device
from Experiment import Experiment
from Port import Port
from timecourse import CONFIG_PATH, resource_path, measure_temp, measure_voltage, per_iteration
from timecourse import get_measurement_row, append_list_to_tsv, kill_switch, lists_to_dictlist
import timecourse
import random
import time
import sys

"""
The goal is to be able to do everything that the app does but without shiny
Then pull in the functions into the shiny app
Shiny is mostly a navigation and display system, not a data handler system
"""


def test_device_and_port_init():
    """
    if the devices is created outside of this function, it is duplicated
    this leaves 2 devices in Device.alls and 32 ports in Port.all
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
    assert type(Port.all) is list
    assert d.ports[n] in Port.all
    assert d.ports[1].usage == 0
    assert d.ports[9].users == []
    assert d.ports[11].usage == 1
    assert d.ports[11].users == ["test"]
    assert d.ports[1].position == 2
    assert type(d.ports[1].position) == int
    assert Device.all[0] is d
    assert len(Port.all) == 16
    assert len(Device.all) == 1
    assert [p for p in Port.all if p.usage == 1] == [d.ports[11]]
    #NEED TO MAKE TEMP FOLDER FOR tests assert load_pickle()=={"Devices":[],"Experiments":[],"Experiment_names":[]}
    
def test_pickle_methods():
    d = Device.all[0] 
    d2 = Device("gamble", 320218)
    assert d.__class__.__name__ == "Device"
    Experiment.add_to_pickle(device = d) 
    devices = Experiment.load_pickle()["Devices"]
    Experiment.reconcile_pickle()
    devices = Experiment.load_pickle()["Devices"]
    assert len(devices) == 2
    
def test_port_methods():
    """
    Don't make new d, call it from the class variable. 
    It passes from one method to another, saved in the Class itself
    """
    d = Device.all[0] 
    n = 3
    assert len(Device.all) == 2
    assert d.ports[n].position == n+1
    assert len(Port.all) == 32
    assert len(Device.all) == 2
    assert Port.report_available_ports() == [p for p in Port.all if p.usage == 0]
    assert [p.position for p in Port.report_available_ports()] == [1,2,3,4,5,6,7,8,9,10,11,13,14,15,16] + list(range(1,17))
    assert Port.count_available_ports() == 31
    assert Port.report_ref_ports() == []
    Port.remove_user("test")
    assert Port.count_available_ports() == 32
    
def test_device_methods():
    """
    these are labJack-specific and require one or more Labjacks to be connrected
    """
    pass

def test_experiment():
    d = Device.all[0]
    test_ports = d.ports[1:17]
    ref_port = d.ports[0]
    t = Experiment("test_experiment", 10, ref_port, test_ports)
    assert t.name == "test_experiment"
    assert len(t.test_ports) == 15
    assert len(t.test_blanks) == 15
    assert Experiment.all == [t]
    assert t.blanks_needed() == test_ports + [ref_port]
    t.start_experiemnt()


def test_timecourse_without_device(mocker):
    def voltages(sn, ports:list):
        return [random.uniform(0.1, 2.3) for x in ports]
    def temperature(sn):
        return random.uniform(220, 400)
    def output_row(input):
        return input

    #test utility methods
    keys = ["a","b","c","d", "d", "d"]
    values = [1,2,3,4,5,6]
    assert lists_to_dictlist(keys, values) == {"a":[1], "b":[2], "c":[3], "d":[4,5,6]}
    
    #
    measure_temp = MagicMock(side_effect = temperature)
    measure_voltage = MagicMock(side_effect = voltages)
    save_row = MagicMock(side_effect = output_row)
    sys.exit = MagicMock(side_effect = None)
    starttime = time.monotonic()
    d = Device.all[0]
    test = lists_to_dictlist([d.sn for x in range(1,6)], list(range(1,6)))
    assert test == {d.sn:list(range(1,6))}
    spy = mocker.spy(timecourse, "get_measurement_row")
    per_iteration("test_experiment", starttime, d.sn, 0, test, 2.3, [1,1,1,1,1]) #per_iteration has changed since
    assert spy.call_count == 1
    measure_voltage.assert_any_call(d.sn, ports = [0])
    measure_voltage.assert_called_with(d.sn, ports = list(range(1,6)))
    measure_temp.assert_called_with(d.sn)
    sys.exit.assert_not_called()
    t = Experiment.all[0]
    t.stop_experiment()
    per_iteration("test_experiment", starttime, d.sn, 0, test, 2.3, [1,1,1,1,1])
    sys.exit.assert_called_once()
    save_row.assert_called_with(["#Self terminating because run was removed from the pickle file."])


if __name__ == "__main__":
    import pytest 
    pytest.main()
    