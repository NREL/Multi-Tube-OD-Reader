from Device import Device
import pandas as pd
from matplotlib import pyplot as plt
from time import sleep

settings = [5,2.6]

Device.discovery()
d = Device.all[0]
d.read_calibration(d.ports, step =0, dac_set = settings)
voltages = [p.cal0 for p in d.ports]
sleep(3)
d.read_calibration(d.ports, step = 2, dac_set = settings)
voltages2 = [p.cal1 for p in d.ports]

df = pd.DataFrame({"V0": voltages, "V-tube": voltages2})

plt.scatter(voltages, voltages2)
plt.show()


from Device import Device
from Experiment import reconcile_pickle
from time import sleep
reconcile_pickle()
d1, d2 = Device.all
d1.name
def check_all(device, voltage):
    for p in device.ports:
        print(device.read_calibration([p], step = 0, dac_set =[5,voltage])[0])
        sleep(2)

d1.name
check_all(d)