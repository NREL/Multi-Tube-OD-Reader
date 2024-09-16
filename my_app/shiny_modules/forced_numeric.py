"""
Shiny "module" to enforce inputs being integers within min/max boundaries.

The out-of-the-box numeric input fails to enforce min and max constraints.
This module enforces constraints by returning replacing an out-of-bounds
value with either min or max (whichever is relevent). Returns output to input,
creating a recursive correction for compount

See setup_run.py or setup_run.py modules for usage examples. This implimentation uses takes a
reactive.Value as input for max. Can easily be modified to accept reactive or non-reactive inputs. 

Modules imported:
- shiny.module: Provides the ability to define and use Shiny modules.
- shiny.ui: Contains functions for creating Shiny UI components.
- shiny.reactive: Provides reactive programming features for Shiny apps.
- shiny.render: Contains functions for rendering outputs in a Shiny app.
- shiny.req: A utility function to ensure certain conditions are met before proceeding.
"""

from shiny import module, ui, reactive, render, req

@module.ui
def controlled_numeric_ui():
    """
    Returns a ui.input_numeric, but with boundaries enforced.
    """
    return ui.output_ui("numeric")

@module.server
def controlled_numeric_server(input, output, session, my_label, my_value, my_min, my_max):
    """
    Defines the server logic for a controlled numeric input component.

    Args:
        my_label (str): The label for the numeric input field.
        my_value (int): The initial value for the numeric input.
        my_min (int): The minimum value allowed for the numeric input.
        my_max (reactive.Value): A reactive expression that provides the maximum value allowed for the numeric input.
        (Inputs can easily be modified to accept reactive or non-reactive variables)

    Returns:
        reactive.Value: The reactive value representing the current value of the numeric input.

    To do:
        generalize to accept both reactive and non-reactive inputs throughout.
    """    

    @output
    @render.ui
    def numeric():
        """
        Renders the numeric input UI component with the specified label, initial value, 
        minimum value, and maximum value.

        Returns:
            ui.InputNumeric: The numeric input UI component.

        Rendered by:
            ui.output_ui("numeric")
        """
        return ui.input_numeric("controlled_numeric", my_label, value = my_value,  min = my_min, max =my_max())
    
    @reactive.calc
    def corrected_value():
        """
        Corrects value to be within min/max boundaries.

        Values already within boundaries are returned unchanged.
        Module is recursive, correcting multiple problems per iteration
        The native numeric input already rejects all non-number characters

        """
        val = input.controlled_numeric()
        
        #Empty inputs cause problems.
        #check for none and return default, in my case 1
        if val is None:
            return 1
        
        #round non-int floats to whole numbers
        if not isinstance(val, int) and isinstance(val, float):
            return round(val)
        
        #adjust to nearest boundary
        if val > my_max() :
            return my_max()
        if val < my_min :
            return my_min    
        
    @reactive.effect
    @reactive.event(corrected_value)
    def _():
        """
        Replaces the UI input with a new input box with the corrected value.
        """
        ui.update_numeric("controlled_numeric", label=my_label, value=corrected_value(), min = my_min, max = my_max())

    return input.controlled_numeric

