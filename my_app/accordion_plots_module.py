import sys
from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
import pandas
import pickle
import app
from sampling import set_usage_status, melted_df_to_plot
import psutil
import json
import os

@module.ui
def accordion_plot_ui(value="value"):
    return ui.accordion_panel(
                        ui.output_text("experiment_name"),
                        ui.output_plot("experimental_plot"),
                        ui.input_action_button("stop_run", "Stop Run"),
                    value= value
                    )

@module.server
def accordion_plot_server(input, output, session, command_as_list="list"):
    
    @reactive.calc()
    def file_path():
        #check if run as exe or script file, give current directory accordingly
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        to_return = os.path.join(application_path, ("..\\" + command_as_list[11]) )
        return to_return
    
    @output 
    @render.text()
    def experiment_name():
        return command_as_list[11].split(".")[0] #to remove .tsv extension

    @reactive.calc
    def test_ports_used_in_run():
        usage = json.loads(command_as_list[9])
        return usage
       
    @reactive.file_reader(file_path(), interval_secs=10)
    def data():
        return pandas.read_csv(file_path(), delimiter="\t",header=4, comment="#")
        
    @reactive.calc
    def ref_device_port():
        device, port = command_as_list[3].split(":") 
        port = [int(port)]
        device = app.sn_for_name(device)
        return device, port
    
    @output
    @render.plot
    def experimental_plot():
        raw = data()
        return melted_df_to_plot(raw.drop(columns = "Temperature") )

    @reactive.Effect
    @reactive.event(input.stop_run)
    def _():
        confirm_stop = ui.modal("Are you sure you want to stop this run?",
            title = "Stop Run?",
            footer= ui.row(ui.column(6,ui.modal_button("Keep Running")), 
                        ui.column(6,ui.input_action_button("commit_stop", "Stop Run"))),
            easy_close= False,
        )
        ui.modal_show(confirm_stop)

    @reactive.Effect
    @reactive.event(input.commit_stop)
    def _():
        #read-only load the pickle of running experiments
        running_pickle = {}
        with open(app.CURRENT_RUNS_PICKLE, 'rb') as f:
            running_pickle = pickle.load(f)

        #get PID of matching command, returnes first item in list of length 1
        pid = [i for i in running_pickle if running_pickle[i] == command_as_list][0]
        
        #remove PID from running experiments
        running_pickle.pop(pid, None)
        
        #stop the process
        try:
            p = psutil.Process(pid)
            p.terminate()
        except:
            print("Cant find the PID, it must have already stopped")
        ui.notification_show(f"{experiment_name()} ended.")    
        
        #write updated current runs to pickle
        with open(app.CURRENT_RUNS_PICKLE, 'wb') as f:
            pickle.dump(running_pickle, f, pickle.DEFAULT_PROTOCOL)
        
        #mark non-ref tubes from closed run as available for use
        for sn, ports in test_ports_used_in_run().items():
            set_usage_status(sn=sn, ports_list= ports, status = 0)
        
        #do any of the running experiments in the pickle use the given ref port [3] in the command list.
        ref_not_used = True
        for experiment in running_pickle.values():
            if command_as_list[3] == experiment[3]:
                ref_not_used = False
                break #one match is enough, stop the loop

        #set port as available if not used elsewhere. 
        if ref_not_used:
            set_usage_status(sn = ref_device_port()[0], ports_list=ref_device_port()[1], status = 0)
        ui.modal_remove()





