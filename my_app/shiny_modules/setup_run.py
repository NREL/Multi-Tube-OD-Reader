"""
Shiny "module" for setting up and starting a Multi-Tube-OD-Reacer experiment.

The module provides input widgets and options for the user to define
- the experiment name
- the interval between timepoints
- the device to use (in case there are multiple devices connected to the computer)
- the number of growth tubes to test

Controls are enforced to ensure users 
- can't overwrite existing experiment data files
- can't use more ports than currently unused
- can start new experiments (physical and coding objects)

Modules imported:
- classes.device: Contains the Device class for device management.
- classes.port: Contains the Port class for port management.
- classes.experiment: Contains the Experiment class for experiment management.
- shiny.module: Provides the ability to define and use Shiny modules.
- shiny.ui: Contains functions for creating Shiny UI components.
- shiny.reactive: Provides reactive programming features for Shiny apps.
- shiny.render: Contains functions for rendering outputs in a Shiny app.
- shiny.req: A utility function to ensure certain conditions are met before proceeding.
- Path from pathlib: A class for working with filesystem paths.
- sys: Provides access to system-specific parameters and functions.
"""

from shiny import module, ui, reactive, render, req
from shiny_modules.forced_numeric import controlled_numeric_server, controlled_numeric_ui
from classes.device import Device
from classes.port import Port
from classes.experiment import Experiment
from pathlib import Path
import sys

def bad_name(st): 
    '''Returns boolean checking if string contains any character other than space, underscore or alphanumeric'''
    for char in st: 
        if char.isalnum() or char=='_' or char==' ': 
            continue 
        else:
            return True
    return False

def new_panel(title, heading, subheading, ui_elements, cancel_label, commit_label):
    """
    A template for building a series of tab-less pages.

    Pages are navigated by a cancel button on the lower left and continue (commit) 
    button on the right hand side of the page. 

    Usage:
        populate lists of each of the Args. This function can be applied to zipped
        lists to automate UI creation. 
        See "Iterating across two lists" example in 
        https://shiny.posit.co/py/docs/modules.html

    Args:
        title (str): The title of the panel.
        heading (str): The heading to be displayed in the panel.
        subheading (str): The subheading to be displayed in the panel.
        ui_elements (list): A list of UI elements to be included in the panel.
        cancel_label (str): The label for the cancel button.
        commit_label (str): The label for the commit button.
    """

    return ui.nav_panel(None,
        ui.h2({"style": "text-align: center;"}, heading),
        ui.div(
            subheading,
            *ui_elements,
            ui.row(
                ui.column(6, 
                    ui.input_action_button("cancel_" + title, cancel_label, width = '175px', style ="float:right"),
                ),
                ui.column(6, 
                    ui.input_action_button("commit_" + title, commit_label, width = '175px', style ="float:left"),
                ),
            ),
            align = "center",
        ),
        value = title
    )

@module.ui
def setup_ui():
    """
    Defines lists of inputs to for the template defined in new_panel()

    See new_panel() function in this module
    """
    tab_titles = ["info",
                  "device",
                  "start",
                  ]

    tab_headings = ["Info",
                    "Parameters",
                    "Start"
                    ]
    
    tab_subheadings = ["",
                       "",
                       "",
                       ]

    tab_cancel_labels = ["Cancel",
                         "Cancel",
                         "Cancel",
                        ]

    tab_commit_labels = ["Next",
                         "Next",
                         "Start Run",
                        ]

    #each page can collect a custom list of inputs from the user
    tab_ui_elements = [[ui.input_text("experiment_name", "File Name", placeholder = "--Enter Name Here--", value = None),
                            ui.input_numeric("interval", "Timepoint interval (min)", value = 10),
                       ],
                       [ui.output_ui("choose_device"),
                            controlled_numeric_ui("ports_available"), 
                       ],
                       [ui.output_text_verbatim("ports_used_text"),
                       ],
                      ]
    
    #The UI returned by this module
    return ui.page_fluid(
        ui.layout_sidebar(
            ui.sidebar(
                ui.output_text("trouble_shooting_output"), #place holder for development
                ui.markdown(
                    """
                    ### Instructions:
                    1. Set experiment info
                        - Unique file name
                        - No special characters (underscores OK)
                        - Set timepoint interval (in minutes)
                    2. Choose device and number of tubes
                    3. Place tubes in assigned ports
                    4. Start the run
                        - Data are deposited into .tsv file
                    """
                ),
            ),
            
            #This is where the lists are parsed by the template
            ui.navset_hidden(#hidden means no visible tabs
                *[new_panel(a, b, c, d, e, f) for a, b, c, d, e, f in 
                 zip(tab_titles, 
                     tab_headings, 
                     tab_subheadings, 
                     tab_ui_elements, 
                     tab_cancel_labels, 
                     tab_commit_labels,
                     )],
                selected= "info",
                id = "setup_run_navigator",
            ),                  
        ),
    ),

@module.server
def setup_server(input, output, session, main_navs):
    """
    Defines the server logic for setting up and configuring an experiment.

    Args:
        main_navs (reactive.Value): Reactive with current active page in main app.

    Returns:
        return_home (reactive.Value): Changing this value activates main app to reset main_navigation to "Home"
    
    To do:
        can setup_run.py modify the main navigation idependently since the reactive is passed?
    """

    return_home = reactive.Value(0)

    #place inside functions to trigger reactive 
    #recalculation whenever this value is changed
    #value is changed as part of reset after finishing setup.
    reset_counter = reactive.Value(0)

    @reactive.calc
    def nav_on_new_exp():
        """
        Checks if the user is on the 'new_experiment' tab.

        Returns:
            bool: True if on the 'new_experiment' tab, False otherwise.
        """
        if main_navs() == "new_experiment":
            Experiment.reconcile_pickle()
            return True
        return False

    @reactive.calc
    def count_available_ports():
        """
        Calculates the number of available ports.

        See Port.report_available_ports()

        Returns:
            int: The number of available ports.
        """

        #Don't recalculate unless user is on this page
        req(nav_on_new_exp() == True)
        return len(Port.report_available_ports())
    
    @reactive.calc
    def devices_available():
        """
        Provides a dictionary of available devices.

        Dictionary is necessary to have {computer-readable:human-readable} pairs

        Returns:
            dict: A dictionary where keys are device serial numbers and values are device names.
        """        
         
        #Recalculate function as reactive to reset_counter()
        reset_counter()
        return {p.device.sn:p.device.name for p in Port.report_available_ports()}

    @reactive.calc
    def max_ports():
        """
        Calculates the maximum number of ports available for the selected device.

        Returns:
            int: The maximum number of ports available for the selected device.
        """

        #Recalculate function as reactive to reset_counter()
        reset_counter()
        ports = [p for p in Port.report_available_ports() if p.device.sn == input.chosen_device()]
        return len(ports)
    
    #returns reactive value, forced to be between 1 and max_ports()
    #max_ports reactive (without parenthesis) is passed to module
    n_ports_requested = controlled_numeric_server("ports_available", my_label = "Number of Growth Tubes",
                                                  my_value = 1, my_min = 1, my_max = max_ports)

    @output
    @render.ui
    def choose_device():
        """
        Renders radio buttons to choose which device to use for experiment

        Returns:
            ui.InputRadioButtons: The UI component for selecting a device.

        Renderd by:
            ui.output_ui("choose_device")
        """

        #Recalculate function as reactive to reset_counter()
        reset_counter()
        return ui.input_radio_buttons("chosen_device", "Choose a Device", devices_available(), selected = None)
  
    @reactive.calc
    def assigned_test_ports():
        """
        Returns:
            list: A list of ports assigned for observations.
        """
        #Recalculate function as reactive to reset_counter()
        reset_counter()

        all_ports = Port.report_available_ports()
        ports = [p for p in all_ports if p.device.sn == input.chosen_device()] 
        return ports[0:n_ports_requested()]
    
    @output
    @render.text
    def ports_used_text():
        """
        Renders the text indicating which ports the growth tubes should be placed in.

        Returns:
            str: A string listing the ports where growth tubes should be placed.

        Rendered by:
        ui.output_text_verbatim("ports_used_text")
        """

        #Recalculate function as reactive to reset_counter()
        reset_counter()
        
        header = "Place growth tubes in the following ports:"
        lines = [f"Port {port.position} in {port.device.name}" for port in assigned_test_ports()] 
        lines.insert(0, header)
        return "\n".join(lines)
    
    @reactive.calc
    def file_path():
        """
        Constructs the file path for saving the experiment data.

        Returns:
            str: The full file path for the experiment data file.
        """

        #Don't recalculate unless user is on this page
        req(nav_on_new_exp() == True)

        #Path changes if frozen by Py
        if getattr(sys, 'frozen', False):
            # when running as .exe: .exe and .tsv will be in sibling folders
            application_path = Path(sys.executable).parents[1]
        elif __file__:
            # For non-frozen applications, use __file__ to show source directory
            application_path = Path(__file__).parents[2]
        return application_path / "Output Data" / (input.experiment_name()  + ".tsv")
    
    @reactive.Effect
    @reactive.event(file_path)
    def _():
        """ 
        Shows a modal if the file path is invalid or if the experiment name is bad.

        See bad_name() in this module
        """        
        if file_path().exists() or bad_name(input.experiment_name()): 
            file_exists = ui.modal(ui.markdown(
                """
                #### Please use a different name:
                - Special characters are not allowed
                    - Only letters, numbers, spaces and underscores are allowed
                - Names must be different from previous output files
                """
            ),
                title="Invalid Name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(file_exists)
            return 

    ######################## Navigation #############################################
    
    @reactive.Effect
    @reactive.event(input.commit_info)
    def _():
        """
        Handles the commit action on the info tab. 
        
        Validates the experiment name and navigates to the next tab.
        """
        if input.experiment_name() == "" or bad_name(input.experiment_name()):
            no_name = ui.modal(
                "Please enter an valid name before continuing.",
                title="Missing or invalid name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(no_name)
            return  
        ui.update_navs("setup_run_navigator", selected = "device")

    @reactive.Effect
    @reactive.event(input.cancel_info)
    def _():
        """
        Handles the cancel action on the info tab. 
        
        Resets the setup and navigates back to the "Home" tab.
        """

        #activate reset of several key inputs
        reset_switch()
        return_home.set(return_home() + 1)
  
    @reactive.Effect
    @reactive.event(input.commit_device)
    def _():
        """
        Handles the commit action on the device tab and navigates to the new experment Info tab.
        """
        ui.update_navs("setup_run_navigator", selected = "start")

    @reactive.Effect
    @reactive.event(input.cancel_device)
    def _():
        """
        Handles the cancel action on the device tab and navigates back to the new experment Info tab.
        """        
        ui.update_navs("setup_run_navigator", selected = "info")
    
    @reactive.Effect
    @reactive.event(input.commit_start)
    def _():
        """
        Initializes and starts the experiment, then navigates to the main "Home" tab.

        Spins-off a new process to keep experiment running independently
        Records PID in Experiment Object. 

        See Experiment.start_experiment()
        See Experiment class
        """
        #Initialize the experiment object
        current_run = Experiment(name = input.experiment_name(),
                                 interval = input.interval(),
                                 test_ports = assigned_test_ports(),
                                 outfile = file_path())
        
        #Start the new PID to control the hardware
        current_run.start_experiment()

        #returns to main "Home" page to watch data accumulate
        return_home.set(return_home() + 1)

        #activate reset of several key inputs
        reset_switch()

    @reactive.Effect
    @reactive.event(input.cancel_start)
    def _():
        """
        Handles the cancel action on the start tab. Resets the setup process.
        """        
        #activate reset of several key inputs
        reset_switch()

    def reset_switch():
        """
        Resets the setup process to its initial state, clearing selections and inputs.

        Is activated as part of several cancel or the final commit button.
        """
        ui.update_radio_buttons("chosen_device", selected= None)
        ui.update_text("experiment_name", label = "File Name", placeholder= "--Enter Name Here--", value = "")
        ui.update_navs("setup_run_navigator", selected="info")

        #reset switch sends user to main "Home" tab.
        reset_counter.set(reset_counter() + 1)

    #saves app from crashing in case of no connected hardware devices.
    #is rendered by ui.modal_show(no_ports_left) see next block
    no_ports_left = ui.modal(ui.markdown(
        """
        #### Troubleshooting tips:
        - Instrument may be busy, wait a few seconds.
        - Ensure all devices are properly connected
        - Connect another device
        - End current runs to free up space
        """),
        title = "No Ports or Devices Available",
        footer = ui.input_action_button("leave_module", "OK"),
        easy_close= False,
    )

    @reactive.effect
    @reactive.event(count_available_ports)
    def _():
        """
        Renders a modal if there are no available ports or devices when trying to set up a new experiment.
        """        
        if count_available_ports() <=0 and main_navs() == "new_experiment":
            ui.modal_show(no_ports_left)

    @reactive.Effect
    @reactive.event(input.leave_module)
    def _():
        """
        Sends user back to main "Home" tab after user acknowledges lack of available hardware.
        """        
        ui.modal_remove()
        return_home.set(return_home() + 1)

    #processed by server in main app
    return return_home
