from shinyswatch import theme
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
from configure_hardware import configure_ui, configure_server
from setup_run import setup_ui, setup_server
from accordion_plots_module import accordion_plot_ui, accordion_plot_server
from timecourse import CONFIG_PATH
from experiment import Experiment
#from growth_analysis import analysis_ui, analysis_server
import os
import signal

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
                ui.output_text("trouble_1"),
                ui.output_text("trouble_2"),                
            ),
            ui.output_ui("running_experiments"),
        ),
        value = "home"
    ),
    ui.nav_panel(
       "Start New Run",
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
    def config_file():
        return Experiment.all
    
    #configure hardware
    configure_server("config")

    #setup new run
    setup_complete = setup_server("setup", input.front_page)        

   # return_home = analysis_server("analysis")

    counter = reactive.Value(0)

    @reactive.effect
    @reactive.event(config_file) 
    def _():
        server_list =[]
        ui_list = []
        for experiment in Experiment.all:
            if not os.path.exists(experiment.path):
                experiment.stop_experiment()
                continue #move on after removing dead experiment.
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
        return 
    
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
                ##### Restart or reset the app
                This shouldn't stop current runs.\n\n
                
                ##### Disconnect and reconnect the device(s).
                This may stop current runs that are actively taking measurments.\n\n
                
                ##### Delete the "config.dat" file and restart.
                This will stop current runs.
                It's in the same folder where the files are stored (or close by).\n\n
                
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

    """    
    @reactive.effect
    @reactive.event(return_home)
    def _():
        ui.update_navs("front_page", selected = "home")
    """


    @reactive.effect
    @reactive.event(input.new_experiment)
    def _():
        ui.update_navs("front_page", selected = "new_experiment") 


    @reactive.Effect
    @reactive.event(input.close_app, ignore_init= True, ignore_none= True)
    async def _():
        await session.close()
        await session.app.stop()
    
   
    @reactive.Effect
    @reactive.event(input.close_app, ignore_init= True, ignore_none= True)
    async def _():
        await session.close()
        await session.app.stop()
    
    def kill_server():
        os.kill(os.getpid(), signal.SIGTERM)

    session.on_ended(kill_server)

app = App(app_ui, server)
