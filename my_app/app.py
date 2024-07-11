from LabJackPython import Close
from shinyswatch import theme
from shiny import App, Inputs, Outputs, Session, reactive, render, ui, req
from configure_hardware import configure_ui, configure_server
from reconfiguring_setup_new_run import setup_ui, setup_server
from accordion_plots_module import accordion_plot_ui, accordion_plot_server
from timecourse import CONFIG_PATH
import os
from experiment import Experiment
from port import Port

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

app = App(app_ui, server)
