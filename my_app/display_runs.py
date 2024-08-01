from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from timecourse import collect_header
import matplotlib.pyplot as plt
import numpy as np
import pandas


def v_to_OD(header_path, data, cal_data):
    name, interval, device_ids, ports, usage = collect_header(header_path)
    data.rename(columns = {0:"Time (min)", 1:"temp"}, inplace = True)
    output = data.iloc[:, 0:2]
    log_v = data.iloc[:, 2:].apply(np.log10)
    try:
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
    labels = ["Time (sec)", "Time (min)", "Time (hr)", "Time (day)"]
    multipliers = [60, 1, 1/60, 1/1440]
    limits = [0, 2, 60, 1440]
    raw_x = df.iloc[:, 0]
    level = None
    for i, j in enumerate(limits):
        if raw_x.iloc[-1] > j:
            level = i
    final_x = raw_x.apply(lambda x: x*multipliers[level])
    f, ax = plt.subplots()
    for i in df.columns[2:]:
        ax.scatter(x = final_x, y = df.loc[:, i])
    ax.set_xlabel(labels[level]) 
    ax.set_ylabel(ylabel) 
    ax.set_title(name)
    ax.legend(df.columns[2:], loc = "lower right", shadow = True)
    return ax

@module.ui
def accordion_plot_ui(value="value"):
    return ui.accordion_panel(
                        ui.output_text("experiment_name"),
                        ui.output_plot("experimental_plot"),
                        ui.row(ui.column(6,ui.input_action_button("excel_out", "Export Excel File")),
                               ui.column(6,ui.input_action_button("stop_run", "Stop Run"))),
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

    @reactive.calc()
    def cal_data():
        device_id = exp_obj.all_ports[0].device.sn
        try:
            pre_cal = pandas.read_csv(calibration_path, delimiter = "\t",
                                    index_col= [0,1], na_values = "nan", na_filter = True)
            return pre_cal.sort_index().dropna(how = "all").xs(device_id, level = "DeviceID", drop_level = False)
        except:
            return None

    @reactive.file_reader(file_path(), interval_secs = 10)
    def data():
        try:
            data = pandas.read_csv(file_path(), delimiter="\t", comment="#", header = None)
            return v_to_OD(file_path(), data, cal_data())
        except:
            return None, None
        
    @output
    @render.plot
    def experimental_plot():
        req(type(data()[0]) == pandas.DataFrame)
        output, condition= data()
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

    @reactive.effect
    @reactive.event(input.excel_out)
    def _():
        excel_file_name = "".join((exp_obj.name, ".xlsx"))
        ui.notification_show(f"Saving to {excel_file_name}.", type = "message")
        output, condition = data()
        if condition:
            sheetname = "Calibrated ODs"
        else:
            sheetname = "log10(OD)"
        with pandas.ExcelWriter(excel_file_name) as writer:
            output.to_excel(writer, sheet_name = sheetname)
            if cal_data() is not None:
                cal_data().to_excel(writer, sheet_name = "Calibration Data")

            

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
 

