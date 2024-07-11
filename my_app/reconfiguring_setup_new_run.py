from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from LabJackPython import Close
from numeric_module import controlled_numeric_server, controlled_numeric_ui
import os
from device import Device
from port import Port
from experiment import Experiment
from timecourse import resource_path

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

    tab_titles = ["setup", 
                "start",
                ]

    tab_headings = ["Setup a New Run",
                    "Before Starting",
                    ]
    
    tab_subheadings = ["Set Experimental Parameters",
                    "",
                    ]

    tab_cancel_labels = ["Cancel",
                    "Cancel",
                    ]

    tab_commit_labels = ["Next",
                    "Start Run",
                    ]

    tab_ui_elements = [[ui.input_text("experiment_name", "Experiment Name", placeholder = "--Enter Name Here--", value = None),
                            ui.input_numeric("interval", "Timepoint interval (min)", value = 10),
                            ui.output_ui("ref_types"),
                            ui.output_ui("choose_ref_device"),
                            ui.output_ui("choose_ref_port"),
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
                    **Reference port**: 
                        Empty port to detect voltage changes due to temperature fluctuations.

                    ### Instructions:
                    1. Set growth parameters
                        - Set number of growths
                        - Set timepoint interval (in minutes)
                        - Set reference port
                    2. Start Run
                        - Place growth tubes and start detection

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
                selected= "setup",
                id = "setup_run_navigator",
            ),                  
        ),
    ),

@module.server
def setup_server(input, output, session, main_navs):
    
    return_home = reactive.Value(0)

    @reactive.calc
    def trigger():
        if main_navs() == "new_experiment":
            return True
        return False

    @reactive.calc
    def count_available_ports():
        trigger()
        return len(Port.report_available_ports())

    @reactive.calc
    def max_ports():
        return count_available_ports() - int(input.new_ref_port())
    
    n_ports_requested = controlled_numeric_server("ports_available", my_label = "Number of Growth Tubes", my_min = 1, my_max = max_ports)

    @output
    @render.ui
    def ref_types():
        trigger()
        input.commit_start()
        input.cancel_start()
        input.cancel_setup()
        #Options need to be numerical to be accounted in "max_ports"
        if Port.report_ref_ports():
            options = {1: "New", 0:"Existing"}
            selected = 0
        else:
            options = {1:"New"}
            selected = 1
        return ui.input_radio_buttons("new_ref_port", "Create New or Use Existing Reference Tube?", options, selected = selected)

    @reactive.calc
    def possible_ref_ports():
        req(input.new_ref_port())
        input.commit_start()
        input.cancel_start()
        input.cancel_setup()
        if input.new_ref_port() == "1": #Use new port
            ports = Port.report_available_ports()
        elif input.new_ref_port() == "0": #Use existing port
            ports = Port.report_ref_ports()
        return ports
    
    @output
    @render.ui
    def choose_ref_device():
        choices = list(set([port.device.name for port in possible_ref_ports()]))
        return ui.input_radio_buttons("chosen_ref_device", "Choose a Reference Device", choices, selected = None)

    @output
    @render.ui 
    def choose_ref_port():
        req(input.chosen_ref_device())
        input.commit_start()
        input.cancel_start()
        input.cancel_setup()
        device_name = input.chosen_ref_device()
        device = next((x for x in Device.all if x.name == device_name), None)
        choices = [port.position for port in possible_ref_ports() if port in device.ports]
        return ui.input_radio_buttons("chosen_ref_port", "Choose A Reference Port", choices, inline= True, selected = None)

    @reactive.calc
    def assigned_test_ports():
        all_ports = Port.report_available_ports()
        #don't allow ref_port to be assigned as test port
        ports = [p for p in all_ports if p != ref_port() ]
        return ports[0:n_ports_requested()]

    @reactive.calc
    def ref_port():
        ref_device = input.chosen_ref_device()
        ref_pos = input.chosen_ref_port()
        return next((x for x in possible_ref_ports() if x.device.name == ref_device if x.position == int(ref_pos) ), None)


    @output
    @render.text
    def ports_used_text():
        header = "Place growth tubes in the following ports:"
        ref = ' '.join(["\nMake sure that port", str(ref_port().position), "in", ref_port().device.name, "is empty!"])
        lines = [f"Port {port.position} in {port.device.name}" for port in assigned_test_ports()] 
        lines.append(ref)
        lines.insert(0, header)
        return "\n".join(lines)
    
    @reactive.calc
    def file_path():
        return resource_path(input.experiment_name() + ".tsv")
    
    @reactive.Effect
    @reactive.event(file_path)
    def _():
        if os.path.exists(file_path()) or bad_name(input.experiment_name()): 
            file_exists = ui.modal(
                "Please use a different name.",
                "You cannot reuse old names or special characters.",
                title="Invalid Name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(file_exists)
            return 

    ######################## Navigation #############################################
    
    @reactive.Effect
    @reactive.event(input.commit_setup)
    def _():
        if input.experiment_name() == "":
            no_name = ui.modal(
                "Please enter an experiment name before continuing.",
                title="Must assign a name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(no_name)
            return  
        ui.update_navs("setup_run_navigator", selected = "start")

    @reactive.Effect
    @reactive.event(input.cancel_setup)
    def _():
        reset_button()
        return_home.set(return_home() + 1)
  
    @reactive.Effect
    @reactive.event(input.commit_start)
    def _():
        current_run = Experiment(name = input.experiment_name(),
                                 interval = input.interval(),
                                 test_ports = assigned_test_ports(),
                                 ref = ref_port(),
                                 outfile = file_path())
        current_run.start_experiment()
        return_home.set(return_home() + 1)
        reset_button()

    @reactive.Effect
    @reactive.event(input.cancel_start)
    def _():
        reset_button()

    def reset_button():
        available_ports = Port.report_available_ports()
        ui.update_text("experiment_name", label = "Experiment Name", placeholder= "--Enter Name Here--", value = "")
        ui.update_navs("setup_run_navigator", selected="setup")

    no_ports_left = ui.modal("You must stop current runs or reset the app to start a new run",
        title = "All Ports Are Being Used",
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
