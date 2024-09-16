from shiny import module, ui, reactive, render, req
@module.ui
def controlled_numeric_ui():
    return ui.output_ui("numeric")

@module.server
def controlled_numeric_server(input, output, session, my_label, my_value, my_min, my_max):
    
    @output
    @render.ui
    def numeric():
        return ui.input_numeric("controlled_numeric", my_label, value = my_value,  min = my_min, max =my_max())
    
    @reactive.calc
    def fixed_value():
        val = input.controlled_numeric()
        if val is None:
            return 1
        if not isinstance(val, int) and isinstance(val, float):
            return round(val)
        if val > my_max() :
            return my_max()
        if val < my_min :
            return my_min    
        
    @reactive.effect
    @reactive.event(fixed_value)
    def _():
        ui.update_numeric("controlled_numeric", label=my_label, value=fixed_value(), min = my_min, max = my_max())

    return input.controlled_numeric

