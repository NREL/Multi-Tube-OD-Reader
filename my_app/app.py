from LabJackPython import Close
from shinyswatch import theme
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
from Configure_hardware import configure_ui, configure_server
from reconfiguring_setup_new_run import setup_ui, setup_server
from accordion_plots_module import accordion_plot_ui, accordion_plot_server
from sampling import make_usage_status_pickle, make_current_runs_pickle, valid_sn, connected_device
import os
import sys
from my_app.Device import load_pickle, save_pickle, search_for_new_hardware

#check if run as exe or script file, give current directory accordingly
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
elif __file__:
    application_path = os.path.dirname(__file__)

CONFIG_PATH = os.path.join(application_path, "config.dat")

if os.path.isfile(CONFIG_PATH):
    pass
else:
    hardware = search_for_new_hardware()
    save_pickle(CONFIG_PATH, [hardware,[]])

app_ui = ui.page_navbar(
    theme.materia(),
    ui.nav_panel(
        "Home",
        ui.layout_sidebar( 
            ui.sidebar(
                ui.input_action_button("new_experiment", "New Experiment", width = '200px'),
                ui.input_action_button("close_app", "Close App", width = '200px'),
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

    @reactive.file_reader(CONFIG_PATH, priority=-1)
    def CONFIG():
        return load_pickle(CONFIG_PATH)

    @reactive.calc
    def DEVICES():
        return CONFIG()[0]
    
    @reactive.calc
    def CURRENT_RUNS():
        return CONFIG()[1]
    
    #configure hardware
    configure_server("config")

    #setup new run
    setup_complete = setup_server("setup", DEVICES)        

    counter = reactive.Value(0)

    @reactive.effect
    @reactive.event(CURRENT_RUNS) 
    def _():
        server_list =[]
        ui_list = []
        for timecourse in CURRENT_RUNS():
            server_list.append(accordion_plot_server(f"{timecourse.name}_{counter()}", list))
            ui_list.append(accordion_plot_ui(f"{timecourse.name}_{counter()}", timecourse.name))
        counter.set(counter() +1) #creates new names for modules. reusing old names causes problems.
        @output
        @render.ui
        def running_experiments():
            return ui.accordion(*ui_list, id= "experiments_accordion",multiple=False)
        return server_list

    @output
    @render.text
    def running_pickles():
        req(CURRENT_RUNS())
        return [vars(x) for x in CURRENT_RUNS()]
    
    @output
    @render.ui
    def gone_wrong():
        return ui.page_fluid(
            ui.markdown(
                """
                ### What usually goes wrong:
                If there's not option for "Number fo Growth Tubes" for your new run, the device is either disconnected or busy taking meaurements. Retry later\n
                Trying to take two readings simultaneously (mulitple, high frequency runs) can crash the software.\n

                ### Steps to Try: 
                ##### Restart the app
                This won't stop current runs.\n
                
                ##### Disconnect and reconnect the device(s).
                This may stop current runs.\n
                
                ##### Delete the two ".pickle" files.
                - Current_runs.pickle
                - Usage_status.pickle\n
                They are in the same folder as the app, near where the output files are stored.\n
                This will stop current runs at the next time point.
                                  
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

app = App(app_ui, server)