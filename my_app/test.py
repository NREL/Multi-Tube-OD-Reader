import unittest
from objectify_my_app import Device, Timecourse


class TestDeviceObject(unittest.TestCase):
    def test_add_remove_report_ports(self):
        device = Device("Jason", 1323401, 1)
        
        self.assertEqual(type(device.port_usage[0].users), list )
        device.set_usage([11, 12, 13], "new_run", 2)
        self.assertEqual(device.port_usage[10].usage, 2)
        self.assertEqual(device.port_usage[10].users, ["new_run"])
        
        self.assertEqual(device.port_usage[11].usage, 2)
        self.assertEqual(device.port_usage[11].users, ["new_run"])
        
        self.assertEqual(device.port_usage[12].usage, 2)
        self.assertEqual(device.port_usage[12].users, ["new_run"])

        device.set_usage([11], "second_run", 2)
        self.assertEqual(device.port_usage[10].usage, 2)
        self.assertEqual(device.port_usage[10].users, ["new_run", "second_run"])

        device.set_usage([3], "third_run", 2)
        self.assertEqual(device.port_usage[2].usage, 2)
        self.assertEqual(device.port_usage[2].users, ["third_run"])

        device.set_usage([1, 16], "last_run", 1)
        self.assertEqual(device.report_available_ports(), [2,4,5,6,7,8,9,10,14,15])

        self.assertEqual(device.report_ref_ports(), [3,11,12,13])

        device.stop_experiment("new_run")
        self.assertEqual(device.report_available_ports(), [2,4,5,6,7,8,9,10,12,13,14,15])
        self.assertEqual(device.report_ref_ports(), [3,11])

    def test_device_timecourse_interactions(self):
        pass
    
if __name__ == "__main__":
    unittest.main()