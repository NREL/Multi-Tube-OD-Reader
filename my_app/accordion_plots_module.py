from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
import matplotlib.pyplot as plt
import pandas

@module.ui
def accordion_plot_ui(value="value"):
    return ui.accordion_panel(
                        ui.output_text("experiment_name"),
                        ui.output_plot("experimental_plot"),
                        ui.input_action_button("stop_run", "Stop Run"),
                    value= value
                    )

@module.server
def accordion_plot_server(input, output, session, exp_obj):
    
    @reactive.calc()
    def file_path():
        return exp_obj.path
    
    @output 
    @render.text()
    def experiment_name():
        return exp_obj.name
       
    @reactive.file_reader(file_path(), interval_secs = 10)
    def data():
        return pandas.read_csv(file_path(), delimiter="\t", comment="#")
        
    @output
    @render.plot
    def experimental_plot():
        #Change this to plotly, interactive widget to get labels
        try:
            raw = data()
        except pandas.errors.EmptyDataError:
            return None
        raw_col = raw.columns
        temperature_df = raw[raw_col[0:2]]
        od_df = raw.loc[:, raw.columns!=raw_col[1]]
        col = od_df.columns
        fig, ax = plt.subplots()
        ax.set_xlabel("Time (min)")
        ax.set_ylabel("Voltage")
        ax.set_title(exp_obj.name)
        for i, col_name in enumerate(col):
            if i >= 1:
                x = od_df[col[0]]
                y = od_df[col[i]]
                ax.scatter(x, y)
                if len(x) >= 2: #otherwise plot shows error until second timepoint.
                    ax.text(x.iloc[-1], y.iloc[-1], col_name)

        return fig

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
 

