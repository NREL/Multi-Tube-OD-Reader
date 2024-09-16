"""
Shiny "module" for configuring Multi-Tube-OD-Reader hardware.

It includes functionality for selecting a device, renaming it, and triggering a visual indicator (blinking) on the device.

Modules imported:
- shiny.module: Provides the ability to define and use Shiny modules.
- shiny.ui: Contains functions for creating Shiny UI components.
- shiny.reactive: Provides reactive programming features for Shiny apps.
- shiny.render: Contains functions for rendering outputs in a Shiny app.
- shiny.req: A utility function to ensure certain conditions are met before proceeding.
- device.Device: Device class for interacting with the hardware.
"""
from shiny import module, ui, reactive, render, req
from classes.device import Device

@module.ui 
def configure_ui():
    """
    Defines the user interface for configuring hardware devices.

    Returns:
        ui.Page: A fluid page layout containing UI elements for selecting a device,
                 renaming it, and triggering a blink action.
    """    
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
