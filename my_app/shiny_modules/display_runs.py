"""
Shiny "module" for displaying and managing running experiments. 

It includes functionalities for plotting experimental data, exporting data to an Excel file,
and stopping the current run.

Modules imported:
- shiny.module: Provides the ability to define and use Shiny modules.
- shiny.ui: Contains functions for creating Shiny UI components.
- shiny.reactive: Provides reactive programming features for Shiny apps.
- shiny.render: Contains functions for rendering outputs in a Shiny app.
- shiny.req: A utility function to ensure certain conditions are met before proceeding.
- timecourse.collect_header: A function for extracting metadata from a header of the output file.
- matplotlib.pyplot: Used for creating plots.
- numpy: Provides mathematical functions including logarithms.
- pandas: Used for data manipulation and reading/writing data to files.
"""

from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from timecourse import collect_header
import matplotlib.pyplot as plt
import numpy as np
import pandas


def v_to_OD(header_path, data, cal_data):
    """
    Converts voltage data to calibrated optical density (OD) or uncalibrated Log(10) voltages.

    Takes input from experiment-output `.csv` file (header and data) and `calibration.tsv` data
    (if available)

    Args:
        header_path (str): Path to the header file containing experiment metadata.
        data (pandas.DataFrame): DataFrame containing experimental data with time and voltage columns.
        cal_data (pandas.DataFrame): DataFrame containing calibration data.

    Returns a tuple:
        First element: Output dataframe with columns of time, temperature, and readings.
                       Readings are expressed as either OD or log10(voltage).
        Second element: A boolean indicating if readings are as OD.
    """
    name, interval, device_ids, ports, usage = collect_header(header_path)
    data.rename(columns = {0:"Time (min)", 1:"temp"}, inplace = True)
    output = data.iloc[:, 0:2]
    
    #convert to log10(voltages)
    log_v = data.iloc[:, 2:].apply(np.log10)
    
    #return ODs if you can
    try:
        for i, (id, port) in enumerate(zip(device_ids, ports)): 
            slope, intercept, r2, date = cal_data.loc[int(id), int(port)]
            od = log_v.iloc[:, i].apply(lambda y: (y - intercept)/slope)
            output = output.join(od.to_frame(name = port))
        return output, True
    
    #otherwise returns log10(voltages)
    except:
        rename_dict = dict(zip(data.columns[2:], ports))
        output = data.rename(columns = rename_dict)
        return output, False

def make_figure(df, name, ylabel):
    """
    Builds a scatter plot of the experimental data.

    Automatically rescales the time axis to seconds, minutes, hours, days.
    See experimental_plot for rendering the plot.

    Args:
        df (pandas.DataFrame): DataFrame containing time and experimental data.
        name (str): Title of the plot.
        ylabel (str): Label for the y-axis.

    Returns:
        matplotlib.axes.Axes: The axes object of the created plot.
    """    

    #Steps for rescaling the time axis
    labels = ["Time (sec)", "Time (min)", "Time (hr)", "Time (day)"]
    multipliers = [60, 1, 1/60, 1/1440]
    limits = [0, 2, 60, 1440]

    #check which limit is highest
    #could invert this, start at highest limit, stop if true. But list so short, doesn't matter.
    level = None
    raw_x = df.iloc[:, 0]
    for i, j in enumerate(limits):
        if raw_x.iloc[-1] > j:
            level = i #keep index of highest limit reached
    final_x = raw_x.apply(lambda x: x*multipliers[level])
    
    #make plot with rescaled time axis
    f, ax = plt.subplots()
    for i in df.columns[2:]: #column 1 is temperature, this keeps only OD columns
        ax.scatter(x = final_x, y = df.loc[:, i])
    ax.set_xlabel(labels[level]) 
    ax.set_ylabel(ylabel) 
    ax.set_title(name)
    ax.legend(df.columns[2:], loc = "upper left", shadow = True)
    return ax

@module.ui
def accordion_plot_ui(value="value"):
    """
    Defines the user interface for displaying experiment data in an accordion panel.

    Renders an accordion panel with
    - the experiment name
    - a plot of the data (as OD or log10(voltage))
    - a "Stop Run" button
    - an "Export Excel File" button (for ODs. Only raw voltages are automatically stored.)

    Args:
        value (str): The value identifier for the accordion panel.
    """
    return ui.accordion_panel(
                        ui.output_text("experiment_name"),
                        ui.output_plot("experimental_plot"),
                        ui.row(ui.column(6,ui.input_action_button("stop_run", "Stop Run"), align = "center"),
                               ui.column(6,ui.input_action_button("excel_out", "Export Excel File"), align = "center")),
                    value= value
                    )

@module.server
def accordion_plot_server(input, output, session, exp_obj, calibration_path):
    """
    Defines the server logic for the accordion plot module.

    Manages the reactive data processing, plotting, and interactions such as stopping the run and exporting data.

    Args:
        exp_obj (Experiment): The Experiment object containing the experimental data.
        calibration_path (str): Path to the calibration data file.
    """
    @reactive.calc()
    def file_path():
        """Gets path to data file from Experiment Object"""
        return exp_obj.path
    
    @output 
    @render.text()
    def experiment_name():
        """ 
        Gets experiment name from Experiment Object
        
        Rendered by:
            ui.output_text("experiment_name")

        """
        return exp_obj.name

    @reactive.calc()
    def cal_data():
        """
        Loads and processes calibration data from the specified file.

        Returns:
            pandas.DataFrame: DataFrame containing calibration data, or None if loading fails.
        """
        device_id = exp_obj.all_ports[0].device.sn
        try:
            pre_cal = pandas.read_csv(calibration_path, delimiter = "\t",
                                      index_col= [0,1], na_values = "nan", na_filter = True)
            return pre_cal.sort_index().dropna(how = "all").xs(int(device_id), level = "DeviceID", drop_level = False)
        except:
            return None

    @reactive.file_reader(file_path(), interval_secs = 10)
    def data():
        """
        Reads & processes the Experiment data file. See v_to_OD.

        Returns:
            See v_to_OD
        """        
        try:
            data = pandas.read_csv(file_path(), delimiter="\t", comment="#", header = None)
            return v_to_OD(file_path(), data, cal_data())
        except:
            return None, None
        
    @output
    @render.plot
    def experimental_plot():
        """
        Renders the plot for the experimental data.

        Returns:
            See make_figure

        Rendered by:
            ui.output_plot("experimental_plot")
        """        
        #Display "loading" placeholder if data are non-existant
        if type(data()[0]) != pandas.DataFrame:
            f, ax = plt.subplots()
            ax.text(0.5, 0.5, 'loading data', transform=ax.transAxes,
                fontsize=40, color='gray', alpha=0.5,
                ha='center', va='center', rotation=30)
            return ax
        
        #Decide OD vs log10(voltage)
        output, condition= data()
        if condition:
            return make_figure(output, exp_obj.name, "Optical Density")
        else:
            return make_figure(output, exp_obj.name, "log10(Voltage)")

    #Define pop-up/modal to confirm the end of the Experiment.
    confirm_stop = ui.modal("Are you sure you want to stop this run?",
        title = "Stop Run?",
        footer= ui.output_ui("modal_footer"),
        easy_close= False,
    )

    @output
    @render.ui
    def modal_footer():
        """
        Defines the footer of the modal for stopping the run.

        A confirmatory button on the right, an "undo"-like button on left.

        Returns:
            ui.Layout: A layout with buttons to either keep running or stop the run.

        Rendered by:
            ui.output_ui("modal_footer")
        """        
        return ui.layout_columns(ui.input_action_button("cancel_stop", "Keep Running"),
                                 ui.input_action_button("commit_stop", "Stop Run"))
    
    @reactive.effect
    @reactive.event(input.excel_out)
    def _():
        """
        Exports the experimental data and calibration data to an Excel file when the 'Export Excel File' button is clicked.

        The file is named after the experiment and contains the processed data along with calibration data if available.
        A notification informs user that the file is being saved.
        """        
        excel_file_name = "".join((exp_obj.name, ".xlsx"))
        
        #check if OD or Log10(Voltage)
        output, condition = data()
        if condition:
            sheetname = "Calibrated ODs"
        else:
            sheetname = "log10(voltage)"

        #save excel file w/interpreted experiment data and calibration data
        with pandas.ExcelWriter(exp_obj.path.parent / excel_file_name) as writer:
            output.to_excel(writer, sheet_name = sheetname)
            if cal_data() is not None:
                cal_data().to_excel(writer, sheet_name = "Calibration Data")
        
        #a temporary notification message in bottom right corner
        ui.notification_show(f"Saving to {excel_file_name}.", type = "message")

            

    @reactive.Effect
    @reactive.event(input.stop_run)
    def _():
        ui.modal_show(confirm_stop)

    @reactive.Effect
    @reactive.event(input.cancel_stop)
    def _():
        ui.modal_remove()

    @reactive.Effect
    @reactive.event(input.commit_stop)
    def _():
        """
        Stops the experiment and removes the confirmation modal after user confirmation.

        Displays a notification with the result of stopping the experiment.
        Executes Experiment.stop_experiment() method 
        """
        #Reports whether experiment stopped happily or if the 
        #relevant PID could not be found.
        report = exp_obj.stop_experiment()
        ui.modal_remove()
        ui.notification_show(report)   
 

