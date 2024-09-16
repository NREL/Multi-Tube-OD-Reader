from shiny import module, ui, reactive, render, req
from shiny_modules.forced_numeric import controlled_numeric_server, controlled_numeric_ui
import os
from classes.device import Device
from classes.port import Port
from classes.experiment import Experiment
import sys

def bad_name(st): 
    '''Returns False if string contains character other than space, underscore or alphanumeric'''
    for char in st: 
        if char.isalnum() or char=='_' or char==' ': 
            continue 
        else:
            return True
    return False


@module.ui
def setup_ui():
    def new_panel(title, heading, subheading, ui_elements, cancel_label, commit_label):
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

    tab_ui_elements = [[ui.input_text("experiment_name", "File Name", placeholder = "--Enter Name Here--", value = None),
                            ui.input_numeric("interval", "Timepoint interval (min)", value = 10),
                       ],
                       [ui.output_ui("choose_device"),
                            controlled_numeric_ui("ports_available"), 
                       ],
                       [ui.output_text_verbatim("ports_used_text"),
                       ],
                      ]

    return ui.page_fluid(
        ui.layout_sidebar(
            ui.sidebar(
                ui.output_text("trouble_shooting_output"),
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
            ui.navset_hidden(
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
    
    return_home = reactive.Value(0)

    reset_counter = reactive.Value(0)

    @reactive.calc
    def nav_on_tab():
        if main_navs() == "new_experiment":
            Experiment.reconcile_pickle()
            return True
        return False

    @reactive.calc
    def count_available_ports():
        #for controlled_numeric element and for no_ports_left modal
        req(nav_on_tab() == True)
        return len(Port.report_available_ports())
    
    @reactive.calc
    def devices_available():
        reset_counter()
        return {p.device.sn:p.device.name for p in Port.report_available_ports()}

    @reactive.calc
    def max_ports():
        reset_counter()
        ports = [p for p in Port.report_available_ports() if p.device.sn == input.chosen_device()]
        return len(ports) #- int(input.new_ref_port())
    
    n_ports_requested = controlled_numeric_server("ports_available", my_label = "Number of Growth Tubes",
                                                  my_value = 1, my_min = 1, my_max = max_ports)

    @output
    @render.ui
    def choose_device():
        reset_counter()
        return ui.input_radio_buttons("chosen_device", "Choose a Device", devices_available(), selected = None)
  
    @reactive.calc
    def assigned_test_ports():
        reset_counter()
        all_ports = Port.report_available_ports()
        #don't allow ref_port to be assigned as test port
        ports = [p for p in all_ports if p.device.sn == input.chosen_device()] #if p != ref_port() ]
        return ports[0:n_ports_requested()]
    
    @output
    @render.text
    def ports_used_text():
        reset_counter()
        header = "Place growth tubes in the following ports:"
        lines = [f"Port {port.position} in {port.device.name}" for port in assigned_test_ports()] 
        lines.insert(0, header)
        return "\n".join(lines)
    
    @reactive.calc
    def file_path():#Get path to current directory
        req(nav_on_tab() == True)
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        return os.path.join(application_path, input.experiment_name() + ".tsv")
    
    @reactive.Effect
    @reactive.event(file_path)
    def _():
        if os.path.exists(file_path()) or bad_name(input.experiment_name()): 
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
        reset_switch()
        return_home.set(return_home() + 1)
  
    @reactive.Effect
    @reactive.event(input.commit_device)
    def _():
        ui.update_navs("setup_run_navigator", selected = "start")

    @reactive.Effect
    @reactive.event(input.cancel_device)
    def _():
        ui.update_navs("setup_run_navigator", selected = "info")
    
    @reactive.Effect
    @reactive.event(input.commit_start)
    def _():
        current_run = Experiment(name = input.experiment_name(),
                                 interval = input.interval(),
                                 test_ports = assigned_test_ports(),
                                 outfile = file_path())
        current_run.start_experiment()
        return_home.set(return_home() + 1)
        reset_switch()

    @reactive.Effect
    @reactive.event(input.cancel_start)
    def _():
        reset_switch()

    def reset_switch():
        ui.update_radio_buttons("chosen_device", selected= None)
        ui.update_text("experiment_name", label = "File Name", placeholder= "--Enter Name Here--", value = "")
        ui.update_navs("setup_run_navigator", selected="info")
        reset_counter.set(reset_counter() + 1)

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
        if count_available_ports() <=0 and main_navs() == "new_experiment":
            ui.modal_show(no_ports_left)

    @reactive.Effect
    @reactive.event(input.leave_module)
    def _():
        ui.modal_remove()
        return_home.set(return_home() + 1)


    return return_home
