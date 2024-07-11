<<<<<<< HEAD
from LabJackPython import Close
from shinyswatch import theme
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
from Configure_hardware import configure_ui, configure_server
from reconfiguring_setup_new_run import setup_ui, setup_server
from accordion_plots_module import accordion_plot_ui, accordion_plot_server
from timecourse import CONFIG_PATH
import os
from Experiment import Experiment
from Port import Port

#need to add an option within the app to update/reload a dead pickle

if os.path.isfile(CONFIG_PATH):
    pass
else:
    Experiment.reconcile_pickle()
    

app_ui = ui.page_navbar(
    theme.materia(),
    ui.nav_panel(
        "Home",
        ui.layout_sidebar( 
            ui.sidebar(
                ui.input_action_button("new_experiment", "New Experiment", width = '200px'),
                ui.input_action_button("reset_app", "Reset", width = '200px'),
                ui.input_action_button("close_app", "Close App", width = '200px'),
                ui.output_text("trouble_1"),
                ui.output_text("trouble_2"),                
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
        "Identify Hardware",
        configure_ui("config"),
    ),
    ui.nav_panel(
        "When things go wrong",
        ui.output_ui("gone_wrong"),

    ),
    title="MultiTubeOD",
    id = "front_page" 
)

def server(input: Inputs, output: Outputs, session: Session):

    #reconcile on on start up, 
    # will reconcile everytime we add_to_pickle/remove_from_pickle
    Experiment.reconcile_pickle()

    @reactive.file_reader(CONFIG_PATH)
    def pickle():
        return Experiment.all
    
    #configure hardware
    configure_server("config")

    #setup new run
    setup_complete = setup_server("setup", input.front_page)        

    counter = reactive.Value(0)

    @reactive.effect
    @reactive.event(pickle) 
    def _():
        server_list =[]
        ui_list = []
        for experiment in Experiment.all:
            name = experiment.name.replace(" ", "_")
            server_list.append(accordion_plot_server(f"{name}_{counter()}", experiment))
            ui_list.append(accordion_plot_ui(f"{name}_{counter()}", name))
        counter.set(counter() +1) #creates new names for modules. reusing old names causes problems.
        
        @output
        @render.ui
        def running_experiments():
            return ui.accordion(*ui_list, id= "experiments_accordion",multiple=False)
        return server_list

    @output
    @render.text
    def trouble_1():
        pickle()
        try:
            printout1 = []
            for x in Experiment.all:
                printout1 = printout1 + [x.name]
            printout2 = str([p.position for p in Port.all])
            printout3 = str([p.usage for p in Port.all])
    
        except:
            printout = "no experiments yet"
        return "One:\n" + str(printout1) + "\nTWO:\n" + printout2+ "\nThree:\n" + printout3
     
    @output
    @render.text
    def trouble_2():
        Experiment.all
        return 
    
    @output
    @render.ui
    def gone_wrong():
        return ui.page_fluid(
            ui.markdown(
                """
                ### What usually goes wrong:
                Trying to read two experiments on the same device at the same time
                will lead to problems where one or both experiments will quit. \n\n

                ### Other troubleshooting tips:
                ##### Restart the app
                This shouldn't stop current runs.\n\n
                
                ##### Disconnect and reconnect the device(s).
                This may stop current runs.\n\n
                
                ##### Delete the "config.dat" file and restart.
                It's in the same folder where the files are stored (or close by).
                This will stop current runs.\n\n
                
                ### Contact:
                Let me know if things go wrong or what features you'd like to be added.\n
                shebdon@nrel.gov

                """
            ),
        )
    

    ####################### Navigation #######################################

    @reactive.effect
    @reactive.event(setup_complete)
    def _():
        ui.update_navs("front_page", selected = "home")

    @reactive.effect
    @reactive.event(input.new_experiment)
    def _():
        ui.update_navs("front_page", selected = "new_experiment") 

    @reactive.Effect
    @reactive.event(input.close_app)
    async def _():
        await session.close()
        #how to close the terminal when the browser closes?

    @reactive.Effect
    @reactive.event(input.reset_app)
    def _():
        Experiment.reconcile_pickle()

=======
from LabJackPython import Close
from shinyswatch import theme
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
import pickle
from Configure_hardware import configure_ui, configure_server
from setup_new_run import setup_ui, setup_server
from accordion_plots_module import accordion_plot_ui, accordion_plot_server
from sampling import make_usage_status_pickle, make_current_runs_pickle, valid_sn, connected_device
from growth_curve_analysis import analysis_ui, analysis_server
import os
import sys
import logging

#need to get used to logging so I don't have to write/delete print statements
#can move this into a reactive context to respond to a "connect to new hardware" button in the sidebar. 

#move this into the server function
serials = valid_sn()
hardware = {sn:connected_device(sn).getName() for sn in serials}

def name_for_sn(sn):
    return hardware[sn]

def sn_for_name(name):
    for sn, hardware_name in hardware.items():
        if name == hardware_name:
            return sn
Close()

#check if run as exe or script file, give current directory accordingly
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

CURRENT_RUNS_PICKLE = os.path.join(application_path, "Current_runs.pickle")
USAGE_STATUS_PICKLE = os.path.join(application_path, "Usage_status.pickle")


for x in [CURRENT_RUNS_PICKLE, USAGE_STATUS_PICKLE]:
    with open(x ,'a+') as f:
        continue

app_ui = ui.page_navbar(
    theme.materia(),
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
        "Analysis",
        analysis_ui("analysis"),
    ),
    ui.nav_panel(
        "Identify Hardware",
        configure_ui("config"),
    ),
    ui.nav_panel(
        "When things go wrong",
        ui.output_ui("gone_wrong"),

    ),
    title="MultiTubeOD",
    id = "front_page" 
    )

def server(input: Inputs, output: Outputs, session: Session):
    """
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
    """       

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

    #configure hardware
    configure_server("config")

    #setup new run
    setup_complete = setup_server("setup", watch_usage_pickle) 

    analysis_complete = analysis_server("analysis")
    
    @reactive.effect
    @reactive.event(setup_complete)
    def _():
        ui.update_navs("front_page", selected = "home")

    @reactive.effect
    @reactive.event(analysis_complete)
    def _():
        ui.update_navs("front_page", selected = "home")

    @reactive.effect
    @reactive.event(input.new_experiment)
    def _():
        ui.update_navs("front_page", selected = "new_experiment")        

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
        counter.set(counter() +1) #creates new names for modules. reusing old names causes problems.
        @output
        @render.ui
        def running_experiments():
            return ui.accordion(*ui_list, id= "experiments_accordion",multiple=False)
        return server_list


    @output
    @render.text
    def running_pickles():
        req(watch_runs_pickle())
        return [f"{pid}:{list[11]}:{list[3]}" for pid,list in watch_runs_pickle().items()]

    @output
    @render.text
    def status_pickle():
        return watch_usage_pickle()
    
    @output
    @render.ui
    def gone_wrong():
        return ui.page_fluid(
            ui.markdown(
                """
                ### What usually goes wrong:
                If there's no input option for "Number of Growth Tubes" for your new run, the device is either disconnected or busy taking meaurements. Reconnect or retry later\n
                Trying to take two readings simultaneously (mulitple, high frequency runs) can crash the software.\n
                Sometimes the supporting files (with the .pickle extension) get corrupted if runs crash.\n

                ### Steps to Try: 
                ##### Restart the app
                This won't stop current runs.\n
                
                ##### Delete the two ".pickle" files.
                This will stop current runs at the next time point. The files are in the same folder as the app, in a folder where the output files are stored.\n
                - Current_runs.pickle
                - Usage_status.pickle
                                  
                ### Contact:
                Did something go wrong?\n
                Is there a feature you want added?\n
                Let me know!\n
                shebdon@nrel.gov
                """
            ),
        )

>>>>>>> origin/main
app = App(app_ui, server)