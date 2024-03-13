from LabJackPython import Close, LJE_LABJACK_NOT_FOUND
from time import sleep
import u3
import statistics
import pickle
import os
import sys


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

'''
You should use this script in the .py file you're trying to compile with PyInstaller. 
Don't put this code snippet in the .spec file, that will not work. 
Access your files by substituting the path you'd normally type by resource_path("file_to_be_accessed.mp3"). 
Be wary that you should use max' answer for the current version of PyInstaller. 
'''

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


def bad_name(st): 
    '''Returns False if string contains character other than space, underscore or alphanumeric'''
    for char in st: 
        if char.isalnum() or char=='_' or char==' ': 
            continue 
        else:
            return True
        return False

def key_for_value(my_dict:dict, value):
    return list(my_dict.keys())[list(my_dict.values()).index(value)]


@retry(max_retries = 10, wait_time=0.379)
def valid_sn():
    d = u3.openAllU3()
    sn = list(d.keys())
    Close()
    del d
    return sn


def kelvin_to_celcius(k):
    return k-273.15

@retry(max_retries = 4, wait_time = 1)
def configure_device(serialNumber, DAC_voltages, ports):
    d = u3.U3(firstFound = False, serial = serialNumber)
    #set all flexible IOs to analog input
    fio = sum([2**(x-1) for x in ports if x <= 8])
    eio = sum([2**(x-9) for x in ports if x >= 9])
    d.configIO(FIOAnalog = fio, EIOAnalog= eio)
    if DAC_voltages:
        for x,v in enumerate(DAC_voltages):
            d.getFeedback(u3.DAC8(Dac = x, Value = d.voltageToDACBits(v, x )))
    Close()

@retry(max_retries = 40, wait_time = 0.723)
def connected_device(serialNumber):
    return u3.U3(firstFound = False, serial = serialNumber)

def single_measurement(serialNumber, ports:list = [1,2,3,4,5,6,7,8]): 
    try:
        d = connected_device(serialNumber= serialNumber)
    except Exception as e:
        print("LabJack connection problem", e)
    #ports is as on the assembled instrument 1-16, but the labjack refers to 0-15 
    #command_list = [u3.AIN(PositiveChannel=int(x)-1, NegativeChannel=31, LongSettling=True, QuickSample=False) for x in ports]
    bits = d.getFeedback([u3.AIN(PositiveChannel=int(x)-1, NegativeChannel=31, LongSettling=True, QuickSample=False) for x in ports])
    voltages = d.binaryListToCalibratedAnalogVoltages(bits, isLowVoltage= True, isSingleEnded= True, isSpecialSetting= False )
    Close()
    del d
    return voltages
"""
@retry(6,(LJE_LABJACK_NOT_FOUND))
def n_measurements(serialNumber, ports:list = [1,2,3,4,5,6,7,8], n_reps = 3):
    return np.array([single_measurement(serialNumber=serialNumber, ports = ports,) for x in range(n_reps) if sleep(1/n_reps) is None]) 

def average_measurement(array):
    return np.ndarray.tolist(np.mean(array, axis = 0))
"""
@retry(max_retries = 4, wait_time = 1)
def full_measurement(serialNumber, ports:list, n_reps):
    d = u3.U3(firstFound = False, serial = serialNumber)
    #ports are 1-16, but the labjack refers to 0-15
    ports = [int(x) for x in ports]
    fio = sum([2**(x-1) for x in ports if x <= 8])
    eio = sum([2**(x-9) for x in ports if x >= 9])
    d.configIO(FIOAnalog = fio, EIOAnalog= eio)
    data = []
    for x in range(n_reps):
        if sleep(1/n_reps) is None:   
            data.append(d.binaryListToCalibratedAnalogVoltages(d.getFeedback([u3.AIN(PositiveChannel=int(x)-1, NegativeChannel=31, LongSettling=True, QuickSample=False) for x in ports]), isLowVoltage= True, isSingleEnded= True, isSpecialSetting= False ))
    Close()
    del d
    out = []
    for i,first_list in enumerate(data[0]):
        out.append(statistics.mean(list[i] for list in data))
    return out

"""
def stdev_measurement(array = n_measurements):
    return np.std(array, axis = 0)
"""
@retry(max_retries = 4, wait_time = 1)
def get_temp(serialNumber):
   d = u3.U3(firstFound = False, serial = serialNumber)
   temp = kelvin_to_celcius(d.getTemperature())
   Close()
   del d
   return temp

def add_to_file(file_name, list):
    out_file = open(file_name, "a+") #a+ mode creates non-existing file and appends to end if it does exist.
    out_file.write('\t'.join(list) + '\n')
    out_file.close()



#check if run as exe or script file, give current directory accordingly
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

CURRENT_RUNS_PICKLE = os.path.join(application_path, "Current_runs.pickle")
USAGE_STATUS_PICKLE = os.path.join(application_path, "Usage_status.pickle")

PORTS_PER_DEVICE = 16
VALID_SERIAL_NUMBERS = valid_sn()

def make_usage_status_pickle(file = USAGE_STATUS_PICKLE):
    usage_status = {x:[0 for y in range(PORTS_PER_DEVICE)] for x in VALID_SERIAL_NUMBERS}
    with open(file, "wb") as f:
        pickle.dump(usage_status, f, pickle.DEFAULT_PROTOCOL)

def make_current_runs_pickle(file = CURRENT_RUNS_PICKLE):
    with open(file, "wb") as f:
        pickle.dump({}, f, pickle.DEFAULT_PROTOCOL)

def get_usage_status(file = USAGE_STATUS_PICKLE):
    """
    Usage status:
    0 means unused
    1 means in use
    2 means reference in use
    """
    try: 
        with open(file, "rb") as f:
            usage_status = pickle.load(f)
            updated = {device:usage_status[device] for device in VALID_SERIAL_NUMBERS}
            return updated #pickle may contain old devices no longer connected. This obviates those.
    except:
        #usage_status is a dict where Keys:values are serialnumber:list with a 0 for each port.
        make_usage_status_pickle(file = USAGE_STATUS_PICKLE)        
        with open(file, "rb") as f:
            return pickle.load(f)       


def set_usage_status(file = USAGE_STATUS_PICKLE, sn= '320106158', ports_list = [1,2,3,4,5], status = 0):
    """
    Status meaning
    0: unused
    1: used
    2: reference
    """

    usage_status = get_usage_status(file)
    try :
        for port in ports_list:
            usage_status[sn][int(port)-1] = status
    except KeyError:
        if sn in VALID_SERIAL_NUMBERS:
            usage_status[sn] = [0 for y in range(PORTS_PER_DEVICE)]
            for port in ports_list:
                usage_status[sn][int(port)-1] = status 
        else:
            raise KeyError("set_usage_status tried updating an invalid device serial number")
    with open(file, "wb") as f:
        pickle.dump(usage_status, f, pickle.DEFAULT_PROTOCOL)
    return usage_status

def get_unused_ports():
    usage_status = get_usage_status()
    unused_ports = {}
    for device in usage_status.keys():
        unused_ports[device] = [index+1 for index, port in enumerate(usage_status[device]) if port == 0]
    return unused_ports

def flatten_list(input = "listoflists"):
    return [x for xs in input for x in xs]

def get_new_ports(n_ports = 5):
    unused_ports = get_unused_ports()
#    ports_left = len(flatten_list(unused_ports.values()))
    new_ports = {}
#    if ports_left < n_ports:
#        raise ValueError("Not enough ports available in the attached devices. Please attach another device or choose fewer ports.")
    for device, ports in unused_ports.items():                                  #iterate through devices
        new_ports[device] = ports[:n_ports]                                     #collect as many ports as wanted or as available on device (whichever comes first)
        n_ports = n_ports - len(new_ports[device])                              #how many more ports do we need?
        if n_ports == 0:                                                        #stop if we have enough
            break
    return new_ports


