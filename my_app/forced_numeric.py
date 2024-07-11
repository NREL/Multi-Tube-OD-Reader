from shiny import module, ui, reactive, render, req
@module.ui
def controlled_numeric_ui():
    return ui.output_ui("numeric")

@module.server
def controlled_numeric_server(input, output, session, my_label:str = "Can't type out-of-range number", my_min = 1, my_max =100):
    
    @output
    @render.ui
    def numeric():
        return ui.input_numeric("controlled_numeric", my_label, 1,  min = my_min, max =my_max())
    
    @reactive.Effect
    def _():
        req(input.controlled_numeric())
        if not isinstance(input.controlled_numeric(), int):
            return
        if input.controlled_numeric() > my_max() :
            ui.update_numeric("controlled_numeric", label=my_label, value=my_max(), min = my_min, max = my_max())
        if input.controlled_numeric() < my_min :
            ui.update_numeric("controlled_numeric", label=my_label, value=my_min, min = my_min, max = my_max())

    return input.controlled_numeric

