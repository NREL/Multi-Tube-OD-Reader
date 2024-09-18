from LabJackPython import Close
import time
import dill as pickle
import sys
from pathlib import Path
import statistics
import u3

config_file = "config.pkl"

"""
U3-LV has 2 digital-to-analog converters (DAC0 and DAC1)
    DAC0 -> power-switching relay to LEDs & Sensors
    DAC1 -> linear voltage regulator to sensors
"""
DAC_0_1_voltages = [5, 2.6]

def resource_path(relative_path):
    """ Get path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent

    return base_path / relative_path

def get_config_path():
    if getattr(sys, 'frozen', False): #False is the default in case there is no "frozen" attribute
        application_path = Path(sys.executable).parent
    else:
        application_path = Path(__file__).parent
    return (application_path / config_file).resolve()

def retry(max_retries, wait_time):
    """
    Decorator to retry a function if it throws an exception
    """
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
                        time.sleep(wait_time)
                        print(f"Exception given: {e}")
                else:
                    raise Exception(f"Max retries of function {func} exceeded. ")
        return wrapper
    return decorator

#LabJack U3-LV throws exception if connection is busy or not closed
#retry all LabJack U3 interactions in case LabJack is busy taking a reading for a parallel experiment
@retry(max_retries = 4, wait_time = 1)
def measure_voltage(serialNumber, ports:list, n_reps = 9, DAC_voltages = DAC_0_1_voltages):
    """
    Interface with hardware to measure voltages.
    LabJack U3-LV has 16 analog inputs (FIO and EIO called by a sum of powers of 2)
    """
    d = u3.U3(firstFound = False, serial = serialNumber)
    positions = [int(p)-1 for p in ports]
    fio = sum([2**(x) for x in positions if x <= 7])
    eio = sum([2**(x-8) for x in positions if x >= 8])
    d.configIO(FIOAnalog = fio, EIOAnalog= eio)
    
    #set DAC voltages to turn on power/set sensor voltage
    if DAC_voltages:
        for x,v in enumerate(DAC_voltages):
            d.getFeedback(u3.DAC8(Dac = x, Value = d.voltageToDACBits(v, x )))
    
    #repeat measurment n_reps times over y seconds for n_reps and y in the if time.sleep(y/n_reps) statement
    data = []
    for x in range(n_reps):
        if time.sleep(1/n_reps) is None:   
            data.append(d.binaryListToCalibratedAnalogVoltages(d.getFeedback([u3.AIN(PositiveChannel=n, NegativeChannel=31, LongSettling=True, QuickSample=False) for n in positions]), isLowVoltage= True, isSingleEnded= True, isSpecialSetting= False ))
    
    #turn off LEDs/sensors by setting DAC voltages to 0
    for x,v in enumerate([0,0]):
            d.getFeedback(u3.DAC8(Dac = x, Value = d.voltageToDACBits(v, x )))
    Close() #all LabJack U3 devices
    
    #return an average voltage 
    voltages = []
    for i,not_used in enumerate(data[0]):
        #flatten list of lists into list of average voltages
        voltages.append(statistics.mean(row[i] for row in data))
    
    return voltages

#LabJack U3-LV throws exception if connection is not closed
#retry all LabJack U3 interactions in case LabJack is busy taking a reading for a parallel experiment
@retry(max_retries = 4, wait_time = 1)
def measure_temp(serialNumber):
   d = u3.U3(firstFound = False, serial = serialNumber)
   temp = kelvin_to_celcius(d.getTemperature())
   Close()
   del d
   return temp

def kelvin_to_celcius(k):
    return k-273.15

def get_measurement_row(test:dict, starttime):
    temperatures = []
    measurements_row = []
    for device, ports in test.items():
        measurements_row = measurements_row + measure_voltage(device, ports=ports)
        temperatures.append(measure_temp(device))
    temp = statistics.mean(temperatures)
    timepoint = time.monotonic()
    measurements_row.insert(0, temp)
    measurements_row.insert(0, (timepoint - starttime)/60)
    return measurements_row

def lists_to_dictlist(keys, values):
    dict = {}
    for key, value in zip(keys, values):
        if key in dict:
            dict[key].append(value)
        else:
            dict[key] = [value]
    return dict

def append_list_to_tsv(input:list, file):
    input = (str(x) for x in input)
    with open(file, "a+") as f: # "a+" will append or write file
        f.write("\t".join(input))
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
def kill_switch(pickle_path, output_file):
    #controls to shut down otherise-infinite loops 
    #terminate if output file has been renamed/moved/deleted.
    if not Path(output_file).exists():
        sys.exit()

    #terminate if pickle not found
    path_obj = Path(pickle_path)
    if not path_obj.exists():
        append_list_to_tsv([f"#Self terminating. {config_file} does not exist at {path_obj}.",
                            f"#You must have deleted {config_file}."], output_file)   
        sys.exit()

    #terminate if pickle not loadable
    try:
        with path_obj.open('rb') as f:  # Use Path's open() method
            loaded_data = pickle.load(f)["Experiment_names"]
    except Exception as e:
        append_list_to_tsv([f"#self terminating. Could not load {path_obj}"], output_file)
        append_list_to_tsv([f"#{e}"], output_file)        
        sys.exit()

    #terminate if run not found in pickle
    if Path(output_file).stem not in loaded_data:
        append_list_to_tsv(["#Self terminating because run was not found in the pickle file."], output_file)
        sys.exit()

def per_iteration(file, pickle_path, test, starttime, interval, failures):
    try:
        #check kill switch
        #append_list_to_tsv creates missing file
        #must check kill switch first if file deletion/rename/move is a kill switch
        kill_switch(pickle_path = pickle_path, output_file = file)

        new_volts= get_measurement_row(test, starttime)
        #new_OD = voltage_to_OD(ref_voltage_t_zero, t_zero_voltages, new_row)
        append_list_to_tsv(new_volts, file)
        
        #reset
        failures = 0
        
        #wait remainder of interval until next read
        time.sleep(interval - (time.monotonic()-starttime) % interval)

    except Exception as e:
        failures += 1
        
        append_list_to_tsv([f"#{e}"], file) #save exception as commented out line in file
        
        if failures >= 4:
            append_list_to_tsv(["#Stopping timecourse due to failures"], file)
            sys.exit()
        
        time.sleep(2.3)

def collect_header(path):
    with open(path, "r") as f:
        lines = f.readlines()[0:5]
    info, device_names, device_ids, ports, usages= [line.rstrip("\n").split("\t")[1:] for line in lines]
    name, interval = info[0:2]
    interval = float(interval)*60
    return [name, interval, device_ids, ports, usages]

################################# MAIN ######################################################
if __name__ == "__main__":
    #path to ouput data file
    file = sys.argv[1]
    pickle_path = sys.argv[2]
    starttime = time.monotonic()
    name, interval, device_ids, ports, usages= collect_header(file)
    test = lists_to_dictlist(device_ids, ports)

    #print start time to header
    append_list_to_tsv([f"#Start Time:\t{time.asctime()}"], file)

    failures = 0 #track consecutive failed iterations
    while True:
        per_iteration(file = file, test = test, pickle_path = pickle_path,
                      starttime = starttime, interval = interval, failures = failures)