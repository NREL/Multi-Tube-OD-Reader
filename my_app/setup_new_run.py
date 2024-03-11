from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from LabJackPython import Close
from copy import deepcopy
import pickle
from sampling import get_new_ports, flatten_list, full_measurement, set_usage_status, configure_device, bad_name, resource_path
from numeric_module import controlled_numeric_server, controlled_numeric_ui
import subprocess
import json
from asyncio import sleep
import os
import app as app_main

blank_readings = "hello"
test_ports = {}

@module.ui
def setup_ui():
    return ui.page_fluid(
        ui.layout_sidebar(
            ui.sidebar(
                #ui.output_text("ports_blanked_output_text"),
                ui.markdown(
                    """
                    **Blank tube**: 
                        Uninoculated tube, measured once per port at setup.
                    
                    **Reference tube**: 
                        Uninoculated tube, stays a separate port during growth.

                    ### Instructions:
                    1. Set growth parameters
                        - Set number of growths
                        - Set timepoint interval (in minutes)
                        - May be able to use reference from a current run
                    2. Blank ports
                        - Place blank tubes in 1 or more ports
                        - Select the check box for each port with a blank
                        - Click "Blank" to take a T<sub>0</sub> measurement
                        - Repeat until ports are blanked
                    3. Start Run
                        - New tab will open with new run

                    """
                ),
            ),
            ui.navset_hidden(
                ui.nav_panel(None,
                    ui.h2({"style": "text-align: center;"}, "Setup A New Run"),
                    ui.div(
                        "Set Experimental Parameters",
                        ui.input_text("experiment_name", "Experiment Name", placeholder = "--Enter Name Here--", value = None),
                        controlled_numeric_ui("ports_available"), 
                        ui.input_numeric("interval", "Timepoint interval (min)", value = 10),
                        ui.output_ui("universal_ref_checkbox"),
                        ui.row(
                            ui.column(6,
                            ),
                            ui.column(6,
                                ui.input_action_button("commit_setup", "Next"),
                            ),
                        ),
                        style = "align:center",
                    ),
                    value="setup"
                ),
                #put style center here
                ui.nav_panel(None, #this will be replaced by a ui.TagList of ui's, one for each device maybe
                    ui.h2({"style": "text-align: center;"}, "Prepare the Device"),
                    ui.div({"style": "text-align: center;"},
                        ui.h4({"style": "text-align: center;"}, ui.output_text("device_to_blank_text")),
                        ui.output_ui("choice_of_ports_to_blank"),
                        ui.row(
                            ui.column(6,
                                ui.input_action_button("cancel_blanks", "Cancel", width = '200px'),
                                style = "float:right",
                            ),
                            ui.column(6,
                                ui.input_action_button("commit_blanks", "Read Selected Blanks", width = '200px'),
                            ),
                        ),
                    ),
                    value="blanks"
                ),
                ui.nav_panel(None,
                    ui.h2({"style": "text-align: center;"}, "Choose the Reference Tube"),
                    ui.div({"style": "text-align: center;"},
                           "Select a 'Device:Port' pair to use for reference:",
                        ui.output_ui("choose_ref_port"),
                        ui.row(
                            ui.column(6,
                                ui.input_action_button("cancel_reference", "Cancel", width = '200px'),
                                style = "float:right",
                            ),
                            ui.column(6,
                                ui.input_action_button("commit_reference", "Next", width = '200px'),
                            ),
                        ),
                    ),
                    value="reference"
                ),
                ui.nav_panel(None,
                    ui.h2({"style": "text-align: center;"}, "Start The Run"),
                    ui.div({"style": "text-align: center;"},
                        "Place growth tubes in the following ports:",
                        ui.output_text_verbatim("ports_used_text",),
                        ui.row(
                            ui.column(6,
                                ui.input_action_button("cancel_start", "Cancel", width = '200px'),
                                style = "float:right",
                            ),
                            ui.column(6,
                                ui.input_action_button("commit_start", "Start Run", width = '200px'),
                            ),
                        ),
                    ),
                    value="start"
                ),
                id = "setup_run_navigator",
            ),                  
        ),
    ),

@module.server
def setup_server(input, output, session, usage_status_reactive):
    
    ports_blanked = reactive.Value({})
    
    @reactive.calc
    def unused_ports():
        req(usage_status_reactive())
        unused_ports ={}
        for device in usage_status_reactive().keys():
            unused_ports[device] = [i+1 for i, status in enumerate(usage_status_reactive()[device]) if status == 0 ]
        return unused_ports
    
    @reactive.calc
    def reference_ports():
        req(usage_status_reactive())
        reference_ports = {}
        for device in usage_status_reactive().keys():
            reference_ports[device] =[i+1 for i, status in enumerate(usage_status_reactive()[device]) if status == 2]
        return reference_ports, len(flatten_list(reference_ports.values()))
    
    @reactive.calc
    def unused_ports_count():
        return len(flatten_list(unused_ports().values()))

    @reactive.calc
    def max_ports():
        try: 
            count = unused_ports_count() - int(input.universal_reference() == False)
        except:
            count = unused_ports_count() - 1 
        return count
    
    n_ports_requested = controlled_numeric_server("ports_available", my_label = "Number of Growth Tubes", my_min = 1, my_max = max_ports)

    @reactive.calc
    @reactive.event(input.commit_setup)
    def new_ports_ids():
        global blank_readings
        req(n_ports_requested())
        try:
            new_ports = get_new_ports(n_ports = n_ports_requested() + int(input.universal_reference() == False) )
        except:
            new_ports = get_new_ports(n_ports = n_ports_requested() + 1)
        ports_blanked.set({device:[] for device in new_ports.keys()})
        blank_readings = {device:[] for device in new_ports.keys()}
        return new_ports
   
    @reactive.calc
    def current_device_or_ports():
        req(ports_blanked())
        for device, ports in new_ports_ids().items():
            if ports == ports_blanked()[device]:
                continue
            return device, [x for x in ports if x not in ports_blanked()[device]]
            #return inside loop to return only the first device 

    def reset_button():
        global blank_readings
        ports_blanked.set(None)
        blank_readings = {}
        ui.update_text("experiment_name", label = "Experiment Name", placeholder= "--Enter Name Here--", value = "")
        ui.update_navs("setup_run_navigator", selected="setup")
        ui.update_checkbox("universal_ref_checkbox", value=False)

    @reactive.calc
    def sort_blank_readings():
        global blank_readings
        # sort blank readings and ports blanked by the port number, keep pairing.
        local_blanks = deepcopy(ports_blanked())
        for device,ports in local_blanks.items():
            blank_readings[device]=[x for _,x in sorted(zip(ports,blank_readings[device]))]
            local_blanks[device]=sorted(ports)
        ports_blanked.set(local_blanks)

    @reactive.calc
    def chosen_ref_device_port():
        device, port = str(input.chosen_ref()).split(":") 
        port = int(port)
        device = app_main.sn_for_name(device)
        return device, port

    #################   Navigation         ############################
    @reactive.Effect
    @reactive.event(input.commit_setup)
    def _():
        name = input.experiment_name()
        # could be neat to refactor this into a list of conditionals that decide whether the list of modals are produced
        
        if os.path.exists(resource_path(name+".tsv")) or bad_name(name): 
            file_exists = ui.modal(
                "Please use a different name.",
                "You cannot reuse old names or special characters.",
                title="Invalid Name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(file_exists)
            return 
        if name == "":
            no_name = ui.modal(
                "Please enter an experiment name before continuing.",
                title="Must assign a name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(no_name)
            return  
        
        for device in new_ports_ids().keys():
            try:
                configure_device(device, DAC_voltages= [2.5,2.5], ports = [])
            except:
                print("Exception updating in setup new run")
                sleep(1)
                configure_device(device, DAC_voltages= [2.5,2.5], ports = [])
                print("retried configure device")
            Close()
        ui.update_navs("setup_run_navigator", selected="blanks")
        

    @reactive.Effect
    @reactive.event(input.cancel_blanks)
    def _():
        reset_button()

    @reactive.effect
    @reactive.event(input.commit_blanks)
    def _():
        global blank_readings
        local_blanks = deepcopy(ports_blanked())
        measure_blanks = full_measurement(current_device_or_ports()[0], ports=input.choice_of_ports_to_blank(), n_reps= 9)
        for x in measure_blanks:
            blank_readings[current_device_or_ports()[0]].append(x)
        local_blanks[current_device_or_ports()[0]] += [int(x) for x in input.choice_of_ports_to_blank()]
        ports_blanked.set(local_blanks)
        sort_blank_readings()
        if ports_blanked() == new_ports_ids():
            ui.update_navs("setup_run_navigator", selected = "reference")
    
    @reactive.Effect
    @reactive.event(input.commit_reference)
    def _():
        global blank_readings
        local_blanks = deepcopy(ports_blanked())
        device, port = chosen_ref_device_port()
        #read blank for reference port
        if port not in local_blanks[device]:
            blank_readings[device].append(full_measurement(device, ports=[port], n_reps= 9)[0])
            local_blanks[device].append(port)
            ports_blanked.set(local_blanks)
        sort_blank_readings()
        ui.update_navs("setup_run_navigator", selected = "start")

    @reactive.Effect
    @reactive.event(input.cancel_reference)
    def _():
        reset_button()

    @reactive.Effect
    @reactive.event(input.cancel_start)
    def _():
        reset_button()
    
    @reactive.Effect
    @reactive.event(input.commit_start)
    async def _():
        with ui.Progress(min = 1, max = 15) as bar:
            global test_ports
            global blank_readings
            bar.set(1, message = "Starting Run")
            ref = input.chosen_ref()
            blanks = json.dumps(blank_readings)  
            ports = json.dumps(ports_blanked())  
            test = json.dumps(test_ports)        
            name = input.experiment_name()
            safe_name = name.replace(' ', '_')
            t= input.interval()
            path_to_new_run_script = resource_path("new_run.py")
            command = ["python", path_to_new_run_script, "-ref", ref, "-blanks", blanks, "-ports", ports, "-test", test, "-o", f"{safe_name}.tsv", "-t", f"{t}"]
            pid = subprocess.Popen(command, creationflags = subprocess.CREATE_NO_WINDOW).pid
            for i in range(1, 8):
                bar.set(i, message = "Starting Run", detail= "Measuring voltages")
                await sleep(0.2)  #startup samples take 2 seconds. If we update pickle too soon, the accordion_server crashes for no file.
            # update the pickles 
            for sn, ports in test_ports.items():
                set_usage_status(sn = sn, ports_list= ports, status = 1)
            device, port = chosen_ref_device_port()
            set_usage_status(sn = device, ports_list=[port], status = 2)
            running_experiments = {}
            try:
                with open(app_main.CURRENT_RUNS_PICKLE, 'rb') as f:
                    running_experiments = pickle.load(f)
            except EOFError:
                None #This get's thrown if the pickle is empty, empty pickle isn't a problem
            running_experiments[pid]=command
            for i in range(7, 16):
                bar.set(i, message = "Starting Run", detail= "Calculating OD")
                await sleep(0.2)  #startup samples take 2 seconds. If we update pickle too soon, the accordion_server crashes for no file.
            with open(app_main.CURRENT_RUNS_PICKLE, 'wb') as f:
                pickle.dump(running_experiments, f, pickle.DEFAULT_PROTOCOL)               
            reset_button()

    ####################### Outputs ####################
    """ 
    @output
    @render.text
    def ports_blanked_output_text():
        return ports_blanked()
    """

    @output
    @render.ui
    def universal_ref_checkbox():
        if reference_ports()[1] >= 1: 
            return ui.input_checkbox("universal_reference", "Use an existing reference?")
    @output
    @render.ui
    def choice_of_ports_to_blank():
        req(current_device_or_ports())
        return ui.input_checkbox_group("choice_of_ports_to_blank", "Mark the ports to blank first", choices = current_device_or_ports()[1], inline= True)
    
    @output
    @render.text
    def ports_used_text():
        req(input.chosen_ref())
        req(ports_blanked())
        global test_ports
        device, port = chosen_ref_device_port()
        test_ports = deepcopy(ports_blanked())
        test_ports[device].pop(test_ports[device].index(port))
        pre_text = ["\n".join([str(app_main.name_for_sn(key)), ",".join(map(str, values))]) for key,values in test_ports.items()]
        return '\n\n'.join(pre_text)

    @output
    @render.text
    def device_to_blank_text():
        req(current_device_or_ports())
        input.commit_blanks()
        input.cancel_blanks()
        input.commit_setup()
        return f"Ports from {app_main.name_for_sn(current_device_or_ports()[0])} to blank next:"
    
    @output
    @render.ui
    @reactive.event(input.commit_blanks)
    def choose_ref_port():
        req(ports_blanked())
        choices = []
        for device, ports in ports_blanked().items():
            for x in ports:
                choices.append(f"{app_main.name_for_sn(device)}:{x}") 
        try: #input.universal_reference() may not be defined. I don't know how to deal with  potentially non-existant variables except to try them
            if input.universal_reference() is not None and input.universal_reference() == True: 
                choices = []
                for device, ports in reference_ports()[0].items():
                    for x in ports:
                        choices.append(f"{app_main.name_for_sn(device)}:{x}")
        except: None
        return ui.input_radio_buttons("chosen_ref", label= "Make sure the Reference Tube is in place before proceeding.", choices=choices, selected = None)
           
    return input.commit_start
