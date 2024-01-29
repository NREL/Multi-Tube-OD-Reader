import u3
from LabJackPython import Close
from Configure_hardware import configure_ui, configure_server
from setup_new_run import setup_ui, setup_server
from accordion_plots_module import accordion_plot_ui, accordion_plot_server
import shinyswatch
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
import pickle
from sampling import make_usage_status_pickle, make_current_runs_pickle
from time import sleep


all_U3 = u3.openAllU3()
serials = list(all_U3.keys())
hardware = {sn:all_U3[object].getName() for sn, object in zip(serials, all_U3)}
Close()

def name_for_sn(sn):
    return hardware[sn]

def sn_for_name(name):
    for sn, hardware_name in hardware.items():
        if name == hardware_name:
            return sn

CURRENT_RUNS_PICKLE = "Current_runs.pickle"
USAGE_STATUS_PICKLE ="Usage_status.pickle"
for x in [CURRENT_RUNS_PICKLE, USAGE_STATUS_PICKLE]:
    with open(x ,'a+') as f:
        continue

app_ui = ui.page_navbar(
    shinyswatch.theme.materia(),
    ui.nav_panel(
        "Home",
        ui.layout_sidebar( 
            ui.sidebar(
                ui.input_action_button("new_experiment", "New Experiment", width = '200px'),
                ui.output_text("running_pickles"),
                ui.output_text("status_pickle"),                
            ),
            ui.output_ui("running_experiments"),
        ),
        value = "home"
    ),
    ui.nav_panel(
       "Start New Run",
        #hidden_tabs_ui("test"),
        setup_ui("setup"),
        value = "new_experiment"
    ),
    ui.nav_panel(
        "Configure Hardware",
        configure_ui("config"),
    ),
    title="MultiTubeOD",
    id = "front_page" 
    )

def server(input: Inputs, output: Outputs, session: Session):
    
    @reactive.Effect
    def _():
        global hardware
        if hardware == {}:
            no_labjack_connection = ui.modal("Please connect a device and restart the program.",
                title = "No Devices Detected",
                footer = ui.input_action_button("close_app", "Exit App"),
                easy_close= False
            )
            ui.modal_show(no_labjack_connection)

    @reactive.Effect
    @reactive.event(input.close_app)
    async def _():
        await session.close()
        #how to close the terminal when the browser closes?
       

    @reactive.file_reader(CURRENT_RUNS_PICKLE, priority=-1)
    def watch_runs_pickle():
        try:
            with open(CURRENT_RUNS_PICKLE, 'rb') as f:
                return pickle.load(f)
        except:
            make_current_runs_pickle()
    
    @reactive.file_reader(USAGE_STATUS_PICKLE)
    def watch_usage_pickle():
        try:
            with open(USAGE_STATUS_PICKLE, 'rb') as f:
                return pickle.load(f)
        except:
            make_usage_status_pickle()

    configure_server("config")

    setup_server("setup", watch_usage_pickle)

    @reactive.effect
    @reactive.event(input.new_experiment)
    def _():
        ui.update_navs("front_page", selected = "new_experiment")        

    """
    @reactive.effect
    @reactive.event(run_started())
    def _():
        req(run_started())
        ui.update_navs("front_page", selected = "home")
    """
    counter = reactive.Value(0)

    @reactive.effect
    @reactive.event(watch_runs_pickle) 
    def _():
        server_list =[]
        ui_list = []
        for list in watch_runs_pickle().values():
            experiment_name = list[11].split(".")[0]
            server_list.append(accordion_plot_server(f"{experiment_name}_{counter()}", list))
            ui_list.append(accordion_plot_ui(f"{experiment_name}_{counter()}", experiment_name))
        counter.set(counter() +1) #creates new names for modules. reusing old names leads to problems.
        @output
        @render.ui
        def running_experiments():
            return ui.accordion(*ui_list, id= "experiments_accordion",multiple=False)
        return server_list


    @output
    @render.text
    def running_pickles():
        req(watch_runs_pickle())
        return [f"{pid}:{list[11]}" for pid,list in watch_runs_pickle().items()]

    @output
    @render.text
    def status_pickle():
        return watch_usage_pickle()

app = App(app_ui, server)
