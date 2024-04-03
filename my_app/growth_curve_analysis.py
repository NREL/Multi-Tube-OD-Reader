from shiny import module, ui, reactive, render, req, Inputs, Outputs, Session
from sampling import make_plot
import statistics
import pandas
import logging
import math
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
                "assign_replicates", 
                "model_fitting",
                ]

    tab_headings = ["Select a File",
                    "Group by Replicates",
                    "Fit Growth Parameters",
                    ]
    
    tab_subheadings = ["Select a '.tsv' file.",
                    "Select a group of replicate ports and assign a name to them.",
                    "Click and drag over the figure to choose the region to model.",
                    ]

    tab_cancel_labels = ["Home",
                    "Cancel",
                    "Cancel",
                    ]

    tab_commit_labels = ["Next",
                    "Next",
                    "Save", 
                    ]

    tab_ui_elements = [[ui.input_file("data_file", label = "Select a Data File", accept = ".tsv"),
                        
                            ],
                        [ui.output_ui("show_replicate_options"),
                         ui.input_text("replica_group_name", "Group Name:"),
                            ],
                        [ui.output_plot("plot1", brush = True),
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
    def data():
        logging.debug("wtf is happening here")
        worked = pandas.read_csv(input.data_file()[0]["datapath"], delimiter = "\t",header = 4, comment = "#")
        logging.debug("we can make file")
        return worked
    
    @reactive.calc
    def replicate_options():
        req(defined_replicate_groups)        
        all_options = list(data().columns)[2:] #slice away time/temp columns 0 and 1
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
    def results():
        #refactor dataframe for easy drawing, assign replicate names to all tubes
        df = data()
        df = df.drop(columns = "Temperature") 
        col_names = df.columns
        time_axis = df.iloc[:, :1] #return first column as df
        group_names = []
        growth_rates = []
        r_squared_values = []
        rename_dict = {}
        summary_df = time_axis #average & stdev of all replicates in group
        
        #process user-defined range of x (time) values 
        try:
            if user_defined_range():
                time_min, time_max = user_defined_range()
            else:
                time_min, time_max = (time_axis.min(), time_axis.max())
        except:
            time_min, time_max = (time_axis.values.min(), time_axis.values.max())
        logging.info("xmin and xmax have values %s and %s", time_min, time_max)

        start_index = int(time_axis.loc[df[col_names[0]] <= time_min].idxmax())
        end_index = int(time_axis.loc[df[col_names[0]] >= time_max].idxmin())
        ln_transformed_df = time_axis.iloc[start_index:end_index, :1]
        logging.info("initiated state of ln_transformed_df ", ln_transformed_df)

        for group_name, columns in defined_replicate_groups().items():
            logging.debug("columns are: %s", columns)

            #average groups of replicate tubes 
            pandas_mean = df[columns].mean(axis = 1)
            pandas_mean.name = f"{group_name}_mean"
            logging.debug('done finding mean of %s', group_name)
            
            #stdev gropus of replicate tubes
            pandas_std = df[columns].std(axis =1)
            pandas_std.name = f"{group_name}_std"
            logging.debug('done finding StDev of %s', group_name)

            #collect avg and stdev of full timecourse
            summary_df.merge(pandas_mean, left_index = True, right_index = True)
            summary_df.merge(pandas_std, left_index = True, right_index = True)
            logging.debug('done merging mean and stdev into df')
            
            #for each individual tube
            for col in columns:
                #poplulate renaming dict to rename later
                rename_dict[col] = group_name

            skip_regression = False
            #for each individual tube, but isolated from prev. loop in case exception kills it.
            for col in columns:
                #natural log transform and model fit the user-defined subset (intended to be log phase)
                try:
                    skip_regression = False
                    ln_transformed = df[col].iloc[start_index:end_index].apply(math.log)
                    ln_transformed_df.merge(ln_transformed, left_index = True, right_index = True)
                except ValueError as ve:
                    print("Cannot perform linear regression. Probably have negative ODs that have undefined natural log.")
                    group_names = ['Problem with Linear Regression']
                    growth_rates = ['Select rage with non-negative ODs']
                    r_squared_values = ['Only the width of the box matters']
                    skip_regression = True
                    break
            logging.info("final state of ln_tranformed_df: %s", ln_transformed_df)
            logging.info("skip_regression value: %s", skip_regression)
            if not skip_regression:
                slope, intercept = statistics.linear_regression(ln_transformed_df[col_names[0]], ln_transformed_df[columns])
                ln_transformed_df[f"{col}_fit_line"] = ln_transformed_df[col_names[0]]*slope + intercept
                growth_rates.append(slope)
                group_names.append(group_name)
                r_squared_values.append(round(statistics.correlation(ln_transformed_df[col_names[0]], list(ln_transformed.values)), 4))
        logging.debug(" rename dict: %s ", rename_dict)
        df.rename(columns=rename_dict, inplace=True) #force duplicate names so make_plot averages them.
        logging.debug('render plot1 renamed df head - {}'.format(df.head().to_string()))
        parameter_df = pandas.DataFrame({'Experiment':group_names, 'Specific Growth Rate': growth_rates, 'R squared':r_squared_values})
        return df, ln_transformed_df, parameter_df, summary_df

    @reactive.calc
    def user_defined_range():
        req(input.plot1_brush())
        dump = input.plot1_brush()
        brushed_range = (dump["xmin"], dump["xmax"])
        logging.debug("user defined range: %s to %s", brushed_range[0], brushed_range[1])
        return brushed_range 

    @output
    @render.plot
    def plot1():
        req(results())
        return make_plot(results()[0])

    
    @output
    @render.plot
    def fitted_plot():

        return 
    
    @output
    @render.table
    def growth_parameter_table():
       req(results())
       return results()[2] 

    @output
    @render.text
    def trouble_shooting_text():
        return input.commit_assign_replicates()
    
    
    return go_home
