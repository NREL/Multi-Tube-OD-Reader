from shiny import module, ui, reactive, render, req
from Device import Device

@module.ui 
def configure_ui():
    return ui.page_fluid(
        ui.h2({"style": "text-align: center;"}, "Configure Hardware"),
        ui.row(
            ui.column(
                6,
                ui.div(
                    ui.output_ui("select_device"),
                    ui.tooltip(
                        ui.input_action_button("blink", "Blink", width = '200px'),
                        "Light up an LED on the device.",
                        placement="bottom",
                        id = "blink_tooltip",
                    ),
                    style="float:right",
                ),
            ),
            ui.column(
                6,
                ui.div(
                    ui.input_text("new_name", "New Name for the Device", placeholder = "--Enter Name Here--", value = ""),
                    ui.tooltip(
                        ui.input_action_button("set_name", "Rename", width = '200px'),
                        "Commit the user-provided name to the selected device.",
                        placement = "bottom",
                        id = "rename_tooltip",
                    ),
                ),
            ),
        ),
    )

@module.server
def configure_server(input, output, session):
    
    @output
    @render.ui
    def select_device():
        choices = {device.sn:device.name for device in Device.all}
        return ui.input_select("device", "Select a Device to interact with", choices=choices)

    @reactive.Effect
    @reactive.event(input.set_name)
    def _():
        req(input.new_name() != "")
        device = next((x for x in Device.all if x.sn == input.device()), None)
        device.rename(input.new_name())
        choices = {device.sn:device.name for device in Device.all}
        ui.update_select("device", label = "Select a Device to interact with", choices = choices)
        ui.update_text("new_name", label = "New Name for the Device", placeholder = "--Enter Name Here--", value = "")

    @reactive.Effect
    @reactive.event(input.blink)
    def _():
        req(input.device())
        device = next((x for x in Device.all if x.sn == input.device()), None)
        device.blink()