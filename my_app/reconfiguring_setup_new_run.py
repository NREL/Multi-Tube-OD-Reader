from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from LabJackPython import Close
from copy import deepcopy
import pickle
from sampling import get_new_ports, flatten_list, full_measurement, set_usage_status, configure_device, bad_name, resource_path
from numeric_module import controlled_numeric_server, controlled_numeric_ui
import subprocess
import json
from asyncio import sleep
import os
import app as app_main
from pathlib import Path
from objectify_my_app import count_available_ports, ref_ports_in_use, available_test_ports, Timecourse, tuples_to_choices

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
                "blanks", 
                "start",
                ]

    tab_headings = ["Setup a New Run",
                    "Prepare the Device",
                    "Start the Run",
                    ]
    
    tab_subheadings = ["Set Experimental Parameters",
                    ui.output_text("device_to_blank_text"),
                    "Place growth tubes in the following ports:",
                    ]

    tab_cancel_labels = ["Cancel",
                    "Cancel",
                    "Cancel",
                    ]

    tab_commit_labels = ["Next",
                    "Read Selected Blanks",
                    "Start Run",
                    ]

    tab_ui_elements = [[ui.input_text("experiment_name", "Experiment Name", placeholder = "--Enter Name Here--", value = None),
                            controlled_numeric_ui("ports_available"), 
                            #ui.input_numeric("ports_available", value = 3, min = 1, max = 16, label = "Number of Growth Tubes to Use:"),
                            ui.input_numeric("interval", "Timepoint interval (min)", value = 10),
                            ui.output_ui("ref_types"),
                            ui.output_ui("ref_port_options"),
                            ],
                        [ui.output_ui("ports_to_blank"),
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
                    **Blank tube**: 
                        Uninoculated tube, measured once per port at setup.
                    
                    **Reference tube**: 
                        Uninoculated tube, stays a separate port during growth.

                    ### Instructions:
                    1. Set growth parameters
                        - Set number of growths
                        - Set timepoint interval (in minutes)
                        - May be able to use reference from a current run
                    2. Blank ports
                        - Place blank tubes in 1 or more ports
                        - Select the check box for each port with a blank
                        - Click "Blank" to take a T<sub>0</sub> measurement
                        - Repeat until ports are blanked
                    3. Start Run
                        - New tab will open with new run

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
def setup_server(input, output, session, devices):
    
    DEVICES = devices

    CURRENT_RUN = None

    @reactive.calc
    def max_ports():
        return count_available_ports(DEVICES())
    
    n_ports_requested = controlled_numeric_server("ports_available", my_label = "Number of Growth Tubes", my_min = 1, my_max = max_ports)

    @output
    @render.ui
    def ref_types():
        if ref_ports_in_use():
            options = {1: "New", 0:"Existing"}
        else:
            options = {1:"New"}
        return ui.input_radio_buttons("universal_ref", "Create New or Use Existing Reference Tube?", options)

    @output
    @render.ui
    def ref_port_options():
        if input.universal_ref():
            ports = available_test_ports(DEVICES())
        else:
            ports = ref_ports_in_use()
        choices = tuples_to_choices(ports) 
        return ui.input_checkbox_group("chosen_ref", "Choose a Reference Device:Port", choices)
            
    @output
    @render.ui
    def ports_to_blank():
        input.commit_blanks
        choices = tuples_to_choices( CURRENT_RUN.blanks_needed() )
        return ui.input_checkbox_group("chosen_blanks", "Choose which Device:Ports to Blank Now", choices)

    ######################## Navigation #############################################
    
    @reactive.Effect
    @reactive.event(input.commit_setup)
    def _():
        name = input.experiment_name()
        # could be neat to refactor this into a list of conditionals that decide whether the list of modals are produced
        
        if os.path.exists(resource_path(name+".tsv")) or bad_name(name): 
            file_exists = ui.modal(
                "Please use a different name.",
                "You cannot reuse old names or special characters.",
                title="Invalid Name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(file_exists)
            return 
        if name == "":
            no_name = ui.modal(
                "Please enter an experiment name before continuing.",
                title="Must assign a name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(no_name)
            return  
        
        CURRENT_RUN = Timecourse(input.experiment_name(), input.interval(), 
                                 input.chosen_ref(),
                                 available_test_ports(DEVICES())[n_ports_requested + 1])

        ui.update_navs("setup_run_navigator", selected="blanks")

    @reactive.Effect
    @reactive.event(input.commit_blanks)
    def _():
        if CURRENT_RUN.blanks_needed():
            CURRENT_RUN.read_blanks(input.chosen_blanks, DEVICES())
        else:
            ui.update_navs("setup_run_navigator", selected = "start")