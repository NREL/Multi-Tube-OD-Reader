from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
import matplotlib.pyplot as plt  
import numpy as np
import pandas
import pickle
import app
from sampling import set_usage_status
import psutil
import time
import json


"""
See add/remove accordion from shiny webpage
https://shiny.posit.co/py/api/ui.remove_accordion_panel.html#shiny.ui.remove_accordion_panel
https://shiny.posit.co/py/api/ui.insert_accordion_panel.html 

"""

@module.ui
def accordion_plot_ui(value="value"):
    return ui.accordion_panel(
                        ui.output_text("experiment_name"),
                        ui.output_text("ports_text"), 
                        ui.output_plot("experimental_plot"),
                        ui.input_action_button("stop_run", "Stop Run"),
                    value= value
                    )

@module.server
def accordion_plot_server(input, output, session, list="list"):
    
    @reactive.calc()
    def file_name():
        return f"C:/Users/shebdon/Documents/GitHub/MultiTubeOD/{list[11]}"
    
    @output
    @render.text()
    def experiment_name():
        return list[11].split(".")[0]

    @reactive.calc
    def test_ports_usage():
        usage = json.loads(list[9])
        return usage
    
    @output
    @render.text
    def ports_text():
        pretty_ports = [f"{app.name_for_sn(sn)}:{ports}" for sn, ports in test_ports_usage().items()]
        "".join(pretty_ports)
        return pretty_ports
    
    @reactive.file_reader(file_name(), interval_secs=10)
    def data():
        try:
            return pandas.read_csv(file_name(), delimiter="\t",header=4)
        except:
            print("can't open file")
            return

        
    @reactive.calc
    def ref_device_port():
        device, port = list[3].split(":") 
        port = [int(port)]
        device = app.sn_for_name(device)
        return device, port
    
    @output
    @render.plot
    def experimental_plot():
        raw = data()
        raw_col = raw.columns
        temperature_df = raw[raw_col[0:2]]
        od_df = raw.loc[:, raw.columns!=raw_col[1]]
        col = od_df.columns
        return plt.plot(od_df[col[0]], od_df[col[1:]],)

    @reactive.Effect
    @reactive.event(input.stop_run)
    def _():
        confirm_stop = ui.modal("Are you sure you want to stop this run?",
            title = "Stop Run?",
            footer= ui.row(ui.column(6,ui.modal_button("Keep Experiment Running")), 
                        ui.column(6,ui.input_action_button("commit_stop", "End the Experiment"))),
            easy_close= False,
        )
        ui.modal_show(confirm_stop)

    @reactive.Effect
    @reactive.event(input.commit_stop)
    def _():
        running_pickle = {}
        with open(app.CURRENT_RUNS_PICKLE, 'rb') as f:
            running_pickle = pickle.load(f)
        try:
            pid = [i for i in running_pickle if running_pickle[i] == list][0]
            running_pickle.pop(pid, None)
        except:
            print("problems collecting a PID")
        try:
            p = psutil.Process(pid)
            p.terminate()
        except:
            print("Cant find the PID, it must have already stopped")
        ui.notification_show(f"{experiment_name()} ended.")    
        with open(app.CURRENT_RUNS_PICKLE, 'wb') as f:
            pickle.dump(running_pickle, f, pickle.DEFAULT_PROTOCOL)
        for sn, ports in test_ports_usage().items():
            set_usage_status(sn=sn, ports_list= ports, status = 0)
        set_usage_status(sn = ref_device_port()[0], ports_list=ref_device_port()[1], status = 0)
        ui.modal_remove()





