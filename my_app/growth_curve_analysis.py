from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from sampling import melted_df_to_plot, growth_rates
import pandas
import logging
from copy import deepcopy

logging.getLogger().setLevel(logging.INFO)

#sidebar: Instructions describing each panel/step
#panel 1: select file to analyze. Buttons = cancel or next
#panel 2: input_checkbox_group, click through which replicates belong to and what is name for group i. buttons = cancel or next
#panel 3: show figure w/names in legend. table of fitted parameters. Default save to .tsv, radio button to safe .png by same name. buttons = cancel or save. 
#Save calculation as comments near header. New cols for fitted values/erros. Include data such as range, replicates, etc. for tracing/reporting
 


@module.ui
def analysis_ui():
    
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

    tab_titles = ["select_file", 
                "raw_figure",
                "assign_replicates", 
                "model_fitting",
                ]

    tab_headings = ["Select a File",
                    "Data for Individual Tubes",
                    "Group by Replicates",
                    "Fit Growth Parameters",
                    ]
    
    tab_subheadings = ["Select a '.tsv' file.",
                    "Save the image, or press continue to group similar replicates",
                    "Select a group of replicate ports and assign a name to them.",
                    "Click and drag over the figure to choose the region to model.",
                    ]

    tab_cancel_labels = ["Home",
                    "Cancel", 
                    "Cancel",
                    "Cancel",
                    ]

    tab_commit_labels = ["Next",
                    "Continue",
                    "Next",
                    "Save", 
                    ]

    tab_ui_elements = [ [ui.input_file("data_file", label = "Select a Data File", accept = ".tsv"), 
                            ],
                        [ui.output_plot("plot", brush = True),
                            ui.output_table("growth_parameter_table")
                            ],
                        [ui.output_ui("show_replicate_options"),
                         ui.input_text("replica_group_name", "Group Name:"),
                            ],
                        [ui.output_plot("plot", brush = True),
                         ui.output_table("growth_parameter_table"),
                            ],
                        ]

    return ui.page_fluid(
        ui.layout_sidebar(
            ui.sidebar(ui.output_text("trouble_shooting_text"),
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
                selected= "select_file",
                id = "analysis_navigator",
            ),
        ),
    )

@module.server
def analysis_server(input, output, session):
    
    ####################### Navigation #####################################

    @reactive.effect
    @reactive.event(input.data_file)
    def _():
        ui.update_navs("analysis_navigator", selected = "assign_replicates")

    @reactive.effect
    @reactive.event(input.commit_select_file)
    def _():
        req(input.data_file)
        ui.update_navs("analysis_navigator", selected = "assign_replicates")  

    @reactive.effect
    @reactive.event(input.cancel_select_file)
    def _():
        logging.debug("made it to cancel select file")
        reset_analysis()
        go_home.set(go_home() + 1)

    @reactive.effect
    @reactive.event(input.commit_assign_replicates)
    def _():
        req(input.show_replicate_options())
        req(input.replica_group_name())
        local_groups = deepcopy(defined_replicate_groups())
        if input.replica_group_name() in local_groups:
            ui.update_text("replica_group_name", label = "Group Name:", value = "")
            name_exists = ui.modal(
                "Please use a unique name.\n",
                "You already have a group of replicates using that name.",
                title="Non-unique Group Name",
                easy_close=True,
                footer=None,
            )
            ui.modal_show(name_exists)
        else:
            logging.debug("Local groups: %s", local_groups)
            local_groups[input.replica_group_name()] = list(input.show_replicate_options())
            defined_replicate_groups.set(local_groups)
            logging.debug("defined_replicate_groups: %s", defined_replicate_groups())
            replicate_options()
            logging.debug(" replicate options in commit assign replicates: %s", replicate_options())
            ui.update_text("replica_group_name", label = "Group Name:", value = "")
            if not replicate_options(): #if we've assigned all replicates to groups and there are no more options
                ui.update_navs("analysis_navigator", selected = "model_fitting")

    @reactive.effect
    @reactive.event(input.cancel_assign_replicates)
    def _():
        reset_analysis()

    @reactive.effect
    @reactive.event(input.commit_model_fitting)
    def _():
        #save fitted model and points for drawing the curve to the .tsv file
        #if radio button save image to separate file, same name, different extension
        logging.debug("going home changed")
        go_home.set(go_home() + 1)

    @reactive.effect
    @reactive.event(input.cancel_model_fitting)
    def _():
        reset_analysis()

    def reset_analysis():
        defined_replicate_groups.set({})
        ui.update_text("replica_group_name", label = "Group Name:", value = "")
        ui.update_navs("analysis_navigator", selected = "select_file")
        ui.update_checkbox_group("show_replicate_options", label = "Mark the Replicate Tubes", choices = replicate_options(), selected = None, inline = True)

    ############################### calcs and outputs
    go_home = reactive.Value(0)

    defined_replicate_groups = reactive.Value({})

    @reactive.calc
    def full_data():
        logging.debug("wtf is happening here")
        df = pandas.read_csv(input.data_file()[0]["datapath"], delimiter = "\t",header = 4, comment = "#")
        return df

    @reactive.calc
    def data():
        req(full_data())
        return full_data().drop(columns = "Temperature")
    
    @reactive.calc
    def temperature_data():
        req(full_data())
        return full_data()["Time (min)", "Temperature"]

    @reactive.calc
    def replicate_options():
        req(defined_replicate_groups)        
        all_options = list(data().columns)[1:] #slice away temp columns 0
        logging.debug(" replicate options function 1: %s", defined_replicate_groups().values())
        for used_options_list in defined_replicate_groups().values():
            print(used_options_list)
            for used_option in used_options_list:
                print(used_option)
                all_options.remove(used_option)
        logging.debug(" replicate options function 2: %s", all_options)
        return all_options

    @output
    @render.ui
    def show_replicate_options():
        req(replicate_options())
        return ui.input_checkbox_group("show_replicate_options", "Mark the Replicate Tubes", choices = replicate_options(), inline = True)

    @reactive.calc
    def brushed_index_range():
        req(input.plot_brush())
        req(data())
        dump = input.plot_brush()
        x_axis= data()["Time (min)"]
        start_index = int(x_axis.loc[x_axis <= dump["xmin"] ].idxmax())
        end_index = int(x_axis.loc[x_axis >= dump["xmax"] ].idxmin())
        logging.debug("user defined range: %s to %s", start_index, end_index)
        return start_index, end_index

    @output
    @render.plot
    def plot():
        df = data().melt(id_vars = ["Time (min)"] )
        
        #require something before using df.replace() to replace individual names with group names, this activates grouped figure
        return melted_df_to_plot(df)
    
    @output
    @render.table
    def growth_parameter_table():
        df = growth_rates(data())
        #require something before calculating average and std of rates
        #maybe melt then df.replace, then aggregate as in melted_df_to_plot
        return df

    @output
    @render.text
    def trouble_shooting_text():
        return input.commit_assign_replicates()
    
    
    return go_home
