"""
Main Shiny app for the Multi-Tube-OD-Reader.

It includes functionality for setting up and managing ongiong experiments, and
for correlating hardware components with software names. 

Structure:
The app has a three tier structure (starting from the core)
1. `timecourse.py` is the minimal script that interprets header info from 
  a `.csv` file into instructions to collect data from the physical device.
2. Helper classes `Experiment`, `Device`, `Port` mirroring their physical counterparts.
3. Other modules for the Shiny app. These pass info between the user and helper classes.

Modules imported:
- shinyswatch.theme: Provides themes for Shiny UI.
- shiny: Core library for building Shiny applications.
- configure_hardware: Shiny "module" for configuring hardware UI and server logic.
- setup_run: Shiny "module" for setting up new runs UI and server logic.
- display_runs: Shiny "module" for displaying and managing ongoing runs.
- experiment.Experiment: Class for managing experiments.
- Path from pathlib: A class for working with filesystem paths.

Constants:
- CALIBRATION_PATH: Path to (an optional) `.csv` file created by the user. Provides 
                    slope-intercept info for calibrating optical density outputs
                    ports in devices. 
"""
from shinyswatch import theme
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
from shiny_modules.configure_hardware import configure_ui, configure_server
from shiny_modules.setup_run import setup_ui, setup_server
from shiny_modules.display_runs import accordion_plot_ui, accordion_plot_server
from timecourse import get_config_path
from classes.experiment import Experiment
from pathlib import Path

#need to add an option within the app to update/reload a dead pickle

Experiment.reconcile_pickle()

CALIBRATION_PATH = get_config_path().parents[0] / "Calibration.tsv"  

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
        "Troubleshooting",
        ui.output_ui("troubleshooting"),
    ),
    title="MultiTubeOD",
    id = "front_page_navs" 
)

def server(input: Inputs, output: Outputs, session: Session):
    """
    Server logic for "Home" tab.

    Main body shows plots of active experiments in a collapsible accordion panel.
    Also manages navigation triggers from this and other Shiny "modules".
    """
    #reconcile on on start up & everytime we 
    #add_to_pickle/remove_from_pickle, see Experiment module
    Experiment.reconcile_pickle()

    @reactive.file_reader(get_config_path())
    def config_file():
        """
        Returns updated list of experiments when app state (config file) changes.
        """
        return Experiment.all
    
    #from configure_hardware.py module
    configure_server("config")

    #from setup_run.py module
    setup_complete = setup_server("setup", input.front_page_navs)        

   # return_home = analysis_server("analysis")

    #makes every reactive recalculation produce a unique ID
    #without this, buttons within accordion module fail
    counter = reactive.Value(0)

    @reactive.effect
    @reactive.event(config_file) 
    def _():
        """
        Creates accordion UI/server elements for active Experiments.
        
        Creates and appends UI and server elements (`display_runs` module)
        for each experiment, and updates the running experiments UI.
        """
        server_list =[]
        ui_list = []
        for experiment in Experiment.all:
            #remove any old inactive experiments
            if not Path(experiment.path).exists():
                experiment.stop_experiment()
                continue 

            #make file name safe as internal ID
            name = experiment.name.replace(" ", "_")

            #populate lists of accordion elements
            server_list.append(accordion_plot_server(f"{name}_{counter()}", experiment, CALIBRATION_PATH))
            ui_list.append(accordion_plot_ui(f"{name}_{counter()}", name))
        counter.set(counter() +1) #creates new names for modules. reusing old names causes problems.
        
        #render lists of accordion elements
        @output
        @render.ui
        def running_experiments():
            """
            Renders list of UI/server elements for active Experiments accordion panel.
            """
            return ui.accordion(*ui_list, id= "experiments_accordion",multiple=False)
        return server_list

    @output
    @render.text
    def trouble_1():
        """
        Placeholder for displaying additional troubleshooting information.
        
        Return is displayed through ui.output_text("trouble_1") UI element.
        """
        return 
    
    @output
    @render.text
    def trouble_2():
        """
        Placeholder for displaying additional troubleshooting information.
        
        Return is displayed through ui.output_text("trouble_2") UI element.
        """
        Experiment.all
        return 
    
    @output
    @render.ui
    def troubleshooting():
        """
        Provides troubleshooting tips and contact information.

        Returns:
            ui.Page: A page/tab containing markdown-formatted troubleshooting tips and contact information.
        """        
        return ui.page_fluid(
            ui.markdown(
                """
                ### What usually goes wrong:
                Trying to read two experiments on the same device at the same time
                will lead to problems where one or both experiments will quit. To
                avoid this, set intervals of parallel experiments to at least 1 minute 
                when running simultaneous experiments.\n\n

                ### Other troubleshooting tips:
                ##### Restart or reset the app
                This shouldn't stop current runs.\n\n
                
                ##### Disconnect and reconnect the device(s).
                This may stop current runs that are actively taking measurments.\n\n
                
                ##### Delete the "config.dat" file and restart.
                This will stop current runs.
                It's in the same folder where the files are stored (or close by).\n\n
                
                ### Support:
                Submit issues at https://github.com/NREL/Multi-Tube-OD-Reader/issues

                Author:
                Skyler Hebdon, PhD. 
                https://www.linkedin.com/in/shebdon
                """
            ),
        )
    

    ####################### Navigation #######################################

    @reactive.effect
    @reactive.event(setup_complete)
    def _():
        """
        Updates the navigation to the home panel after setup is complete.
        """        
        ui.update_navs("front_page_navs", selected = "home")


    @reactive.effect
    @reactive.event(input.new_experiment)
    def _():
        """
        Updates the navigation to the new experiment panel when the 'New Experiment' button is clicked.
        """        
        ui.update_navs("front_page_navs", selected = "new_experiment") 

app = App(app_ui, server)
