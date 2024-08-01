from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from timecourse import collect_header
import matplotlib.pyplot as plt
import numpy as np
import pandas


def v_to_OD(header_path, data, calibration_path):
    name, interval, device_ids, ports, usage = collect_header(header_path)
    data.rename(columns = {0:"time", 1:"temp"}, inplace = True)
    output = data.iloc[:, 0:2]
    log_v = data.iloc[:, 2:].apply(np.log10)
    try:
        pre_cal = pandas.read_csv(calibration_path, delimiter = "\t",
                                index_col= [0,1], na_values = "nan", na_filter = True)
        cal_data = pre_cal.sort_index().dropna(how = "all")
        for i, (id, port) in enumerate(zip(device_ids, ports)): 
            slope, intercept, r2, date = cal_data.loc[int(id), int(port)]
            od = log_v.iloc[:, i].apply(lambda y: (y - intercept)/slope)
            output = output.join(od.to_frame(name = port))
        return output, True
    except:
        rename_dict = dict(zip(data.columns[2:], ports))
        output = data.rename(columns = rename_dict)
        return output, False

def make_figure(df, name, ylabel):
    """y_cols = df.columns[2:]
    x_cols = [0 for x in y_cols]
    return df.plot(x = x_cols, y = y_cols, kind = "scatter",
                   title = name, legend = True, colormap = "gist_earth",
                   xlabel = "Time (min)", ylabel = ylabel)"""
    f, ax = plt.subplots()
    for i in df.columns[2:]:
        ax.scatter(x = df.iloc[:, 0], y = df.loc[:, i])
    ax.set_xlabel("Time (min)") 
    ax.set_ylabel(ylabel) 
    ax.set_title(name)
    ax.legend(df.columns[2:], loc = "lower right", shadow = True)
    return ax

@module.ui
def accordion_plot_ui(value="value"):
    return ui.accordion_panel(
                        ui.output_text("experiment_name"),
                        ui.output_plot("experimental_plot"),
                        ui.input_action_button("stop_run", "Stop Run"),
                    value= value
                    )

@module.server
def accordion_plot_server(input, output, session, exp_obj, calibration_path):
    
    @reactive.calc()
    def file_path():
        return exp_obj.path
    
    @output 
    @render.text()
    def experiment_name():
        return exp_obj.name
       
    @reactive.file_reader(file_path(), interval_secs = 10)
    def data():
        #keep this raw data and v_to_OD separate, in case calibration data is missing
        try:
            return pandas.read_csv(file_path(), delimiter="\t", comment="#", header = None)
        except:
            return None
        
        
    @output
    @render.plot
    def experimental_plot():
        req(type(data()) == pandas.DataFrame)
        output, condition = v_to_OD(file_path(), data(), calibration_path)
        if condition:
            return make_figure(output, exp_obj.name, "Optical Density")
        else:
            return make_figure(output, exp_obj.name, "log10(Voltage)")

    confirm_stop = ui.modal("Are you sure you want to stop this run?",
        title = "Stop Run?",
        footer= ui.row(ui.column(6,ui.modal_button("Keep Running")), 
                    ui.column(6,ui.input_action_button("commit_stop", "Stop Run"))),
        easy_close= False,
    )

    @reactive.Effect
    @reactive.event(input.stop_run)
    def _():
        ui.modal_show(confirm_stop)

    @reactive.Effect
    @reactive.event(input.commit_stop)
    def _():
        report = exp_obj.stop_experiment()
        ui.modal_remove()
        ui.notification_show(report)   
 

