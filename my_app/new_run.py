from LabJackPython import Close
import math
import argparse
from time import time, sleep, monotonic
from datetime import datetime
from json import loads
import app as app_main
import sys
import os
from sampling import configure_device, get_temp, full_measurement, resource_path

t_zero_ref_voltage = None
t_zero_voltage_list = []
parser = argparse.ArgumentParser(description="Collect samples from U3 LabJack instrument, infinit loop.", 
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('-ref', type = str, default= 'Big Red:1', help = 'str(name:port) for choses reference port')
parser.add_argument('-blanks',  type = loads, default = {'320106158':[0.4, 0.4, 0.4, 0.4]}, help="blank_readings dict of sn:[ports for all ports including ref]")
parser.add_argument('-ports',  type = loads, default = {'320106158':[1,2,3,4]}, help="blanked_ports dict of sn[ports] for all ports including ref")
parser.add_argument('-test', type = loads, default = {'320106158':[1]}, help = "test_ports dict of sn:[ports] for non-ref ports")
parser.add_argument('-o', '--out-file', default = 'test.tsv')
parser.add_argument('-t', '--time-interval', type = float, help= "time interval in minute between reads", default=0.05)

args = parser.parse_args()
interval = args.time_interval * 60
ref = args.ref
blanks = args.blanks

file = resource_path( "..\\" + args.out_file)
all_ports = args.ports
test = args.test


ref_device_name, ref_port = ref.split(":")
ref_port = int(ref_port)
ref_device = app_main.sn_for_name(ref_device_name)
ref_blank = blanks[ref_device].pop(all_ports[ref_device].index(ref_port)) #use index in one list to define position in second list

#Still need to figure out how to run the DAQ
def get_header_rows(ref=ref, ref_device=ref_device, ref_blank=ref_blank, test:dict = test, blanks:dict=blanks):
    device_row = ["Device","", ref_device_name]
    port_row = ["Port","", ref_port]
    status_row = ["Status","", "Reference"]
    header_row = ["Time (min)", "Temperature"]
    time_zero_voltages = [ref_blank]
    test = {app_main.name_for_sn(key):val for (key, val) in test.items()}
    for device, ports in test.items():
        for x,port in enumerate(ports): #x is position of port in list, port is port name
            device_row.append(device)
            port_row.append(port)
            status_row.append("Test")
            header_row.append(f"{device}:{port}")
            time_zero_voltages.append(blanks[app_main.sn_for_name(device)][x]) #x means by position
    empty_row = ["" for x in status_row]
    empty_row[0]= datetime.fromtimestamp(time()) #replace first item with date-time
    return [device_row, port_row, status_row, empty_row, header_row], time_zero_voltages

def get_measurement_row(test:dict = test, ref_port = ref_port, ref_device = ref_device):
    temperatures = []
    measurements_row = []
    n_reps = 9
    measurements_row =full_measurement(ref_device, ports=[ref_port], n_reps= n_reps)
    for device, ports in test.items():
        measurements_row = measurements_row + full_measurement(device, ports=ports, n_reps= n_reps)
        temperatures.append(get_temp(device))
    temp = sum(temperatures)/len(temperatures)
    timepoint = monotonic()
    return measurements_row, temp, timepoint

def voltage_to_OD(v_ref_zero, time_zero_voltages, measurements):
    v_ref_now = measurements.pop(0)
    return [math.log10(v_ref_zero/v_ref_now*v_test_zero/v_test_now) for v_test_now, v_test_zero in zip(measurements,time_zero_voltages)]

def save_row(row:list, file = file ):
    row = (str(x) for x in row)
    with open(file, "a") as f:
        f.write("\t".join(row))
        f.write("\n")

header_rows, t_zero_voltage_list=get_header_rows()


with open(file, "a+") as f:
    for row in header_rows:
        row = (str(x) for x in row)
        f.write("\t".join(row))
        f.write("\n")

t_zero_ref_voltage = t_zero_voltage_list.pop(0)
starttime = monotonic()


def per_iteration():
    new_row, temp, timepoint = get_measurement_row()
    new_OD = voltage_to_OD(v_ref_zero = t_zero_ref_voltage, time_zero_voltages=t_zero_voltage_list, measurements=new_row)
    new_OD.insert(0, temp)
    new_OD.insert(0, (timepoint - starttime)/60)
    save_row(new_OD)
    sleep(interval - (monotonic()-starttime) % interval)

while True:
    try:
        per_iteration()
    except Exception as e:
        save_row([f"#{e}"])
