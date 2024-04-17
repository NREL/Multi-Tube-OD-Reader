from LabJackPython import Close
from time import sleep, monotonic
import pickle
import sys
import os
import statistics
import u3


def resource_path(relative_path):
    """ Get path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

#check if run as exe or script file, give current directory accordingly
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

#path to pickle for confirming run is still active
CONFIG_PATH = os.path.join(application_path, "config.dat")



def retry(max_retries, wait_time):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                if retries < max_retries:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        retries += 1
                        sleep(wait_time)
                        print(f"Exception given: {e}")
                else:
                    raise Exception(f"Max retries of function {func} exceeded. ")
        return wrapper
    return decorator

@retry(max_retries = 4, wait_time = 1)
def measure_voltage(serialNumber, ports:list, n_reps = 9, DAC_voltages =[5,2.7]):
    d = u3.U3(firstFound = False, serial = serialNumber)
    #ports are 1-16, but the labjack refers to 0-15
    positions = [int(p)-1 for p in ports]
    fio = sum([2**(x) for x in positions if x <= 7])
    eio = sum([2**(x-8) for x in positions if x >= 8])
    d.configIO(FIOAnalog = fio, EIOAnalog= eio)
    if DAC_voltages:
        for x,v in enumerate(DAC_voltages):
            d.getFeedback(u3.DAC8(Dac = x, Value = d.voltageToDACBits(v, x )))
    data = []
    for x in range(n_reps):
        if sleep(1/n_reps) is None:   
            data.append(d.binaryListToCalibratedAnalogVoltages(d.getFeedback([u3.AIN(PositiveChannel=n, NegativeChannel=31, LongSettling=True, QuickSample=False) for n in positions]), isLowVoltage= True, isSingleEnded= True, isSpecialSetting= False ))
    for x,v in enumerate([0,0]):
            d.getFeedback(u3.DAC8(Dac = x, Value = d.voltageToDACBits(v, x )))
    Close()
    voltages = []
    for i,first_list in enumerate(data[0]):
        voltages.append(statistics.mean(list[i] for list in data))
    return voltages

@retry(max_retries = 4, wait_time = 1)
def measure_temp(serialNumber):
   d = u3.U3(firstFound = False, serial = serialNumber)
   temp = kelvin_to_celcius(d.getTemperature())
   Close()
   del d
   return temp

def kelvin_to_celcius(k):
    return k-273.15

def lists_to_dictlist(keys, values):
    dict = {}
    for key, value in zip(keys, values):
        if key in dict:
            dict[key].append(value)
        else:
            dict[key] = [value]
    return dict

def get_measurement_row(test:dict, ref_port, ref_device):
    temperatures = []
    measurements_row = []
    measurements_row =measure_voltage(ref_device, ports=[ref_port])
    for device, ports in test.items():
        measurements_row = measurements_row + measure_voltage(device, ports=ports)
        temperatures.append(measure_temp(device))
    temp = sum(temperatures)/len(temperatures)
    timepoint = monotonic()
    return measurements_row, temp, timepoint

def save_row(row:list, file):
    row = (str(x) for x in row)
    with open(file, "a+") as f:
        f.write("\t".join(row))
        f.write("\n")
"""
Skip this in favor of voltages: less weight on timecourse
also raw data will answer more questions: Do we need a reference? Do we need a blank? do things change over time.
Also not having a blank/reference will help A LOT with moving around data/controls, etc.
def voltage_to_OD(v_ref_zero, time_zero_voltages, measurements):
    v_ref_now = measurements.pop(0)
    #voltage is proportional to intenisty
    #abs = -log(I/I0) =log(I0/I)
    # A-A(ref) = log(I0/I)-log(I0/I)(Ref)
    #log(A) - log(B) = log(A/B)
    return [math.log10((v_test_zero/v_test_now)/(v_ref_zero/v_ref_now)) for v_test_now, v_test_zero in zip(measurements,time_zero_voltages)]

"""
def per_iteration(experiment_name, starttime, ref_device, ref_port, test, ref_voltage_t_zero, t_zero_voltages, file):
    #save Timepoint, Temp, ODs to new row in output file.
    new_OD, temp, timepoint = get_measurement_row(test, ref_port, ref_device)
    #new_OD = voltage_to_OD(ref_voltage_t_zero, t_zero_voltages, new_row)
    new_OD.insert(0, temp)
    new_OD.insert(0, (timepoint - starttime)/60)
    save_row(new_OD, file)

    #self terminate if pickle not found 
    #keep independent, infinite loops from getting out of control
    try:
        with open(CONFIG_PATH, 'rb') as f:
            running_experiments = pickle.load(f)["Experiment_names"]
    except:
        save_row(["#self terminating because CONFIG file was not found"], file)
        sys.exit()

    #self terminate if run not found in pickle
    #keep independent, infinite loops from getting out of control
    if experiment_name not in running_experiments:
        save_row(["#Self terminating because run was removed from the pickle file."], file)
        sys.exit()



################################# MAIN ######################################################
if __name__ == "__main__":
    #path to ouput data file
    file = resource_path(sys.argv[1])
    
    #collect header info
    with open(file, "r") as f:
        lines = f.readlines()[0:6]
        #split by delimiter, remove left item in table
    info, device_names, device_ids, ports, usages, t_zero_voltages = [line.split("\t")[1:] for line in lines]
    experiment_name, interval = info
    interval = int(interval)*60

    ref_voltage_t_zero = t_zero_voltages.pop(0)
    ref_device = device_ids.pop(0)
    ref_port = ports.pop(0)
    starttime = monotonic()
    test = lists_to_dictlist(device_ids, ports)


    #start iterating, stop if more than 4 consecutive (or near consecutive) failures
    failures = 0
    while True:
        try:
            per_iteration(experiment_name, starttime, ref_device, ref_port, test, ref_voltage_t_zero, t_zero_voltages, file = file)
            if failures > 0:
                failures = failures -1
            #wait remainder of interval until next read
            sleep(interval - (monotonic()-starttime) % interval)
        except Exception as e:
            failures +=1
            save_row([f"#{e}"], file)
            sleep(2.3)
            if failures >= 4:
                save_row(["#Stopping timecourse due to failures"], file)
                sys.exit()
