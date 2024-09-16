"""
Shiny "module" for configuring Multi-Tube-OD-Reader hardware.

It includes functionality for selecting a device, renaming it,
and triggering a visual indicator (blinking) on the device.

Usage:
To distinguish and rename otherwise identical instruments.
1. Select device.
2. Click "Blink" button, watch for blinking LED on instrument.
3. Type in new name for blinking instrument
4. Click "Rename" button

Give user-meaningful names as identifiers such as
- by position: "left", "middle", or "right"
- by location: "MaxQ" or "New Brunswick" named after the incubator
- by usage: "55 C" or "37 C" if you keep them in different
            temperature-dedicated instruments.

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
    Defines the user interface for configuring hardware tab.

    Returns:
        ui.Page: A fluid page layout containing UI elements for selecting a device,
                 renaming it, and triggering a visual indicator (blinking) on the device.
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
    """
    Defines the server logic for configuring hardware.

    This function manages interactions with the UI elements, including selecting a device,
    renaming it, and triggering a visual indicator (blinking) on the device.
    """    
    @output
    @render.ui
    def select_device():
        """
        Creates logic for a dropdown menu for selecting a device from the available devices.

        Rendered by:
            ui.output_ui("select_device"): A dropdown menu for selecting a device.
        """        
        choices = {device.sn:device.name for device in Device.all}
        return ui.input_select("device", "Select a Device to interact with", choices=choices)

    @reactive.Effect
    @reactive.event(input.set_name)
    def _():
        """
        Renames the selected device when the 'Rename' button is clicked.

        Renaming occurs at hardware and software levels.
        Ensures that a new name is provided before proceeding. Updates the dropdown menu
        and clears the text input field after renaming.

        Args:
            input.new_name() from ui.input_text("new_name", ...
            input.device() from ui.input_select("device", ...

        """ 
        #don't react if name is absent
        req(input.new_name() != "")

        #find device object with matching serial number (sn)
        #could create Device.find class function for this.
        device = next((x for x in Device.all if x.sn == input.device()), None)
        
        #print new name to hardware memory and update device object
        device.rename(input.new_name())

        #update dropdown selection options
        choices = {device.sn:device.name for device in Device.all}
        ui.update_select("device", label = "Select a Device to interact with", choices = choices)

        #clear text box
        ui.update_text("new_name", label = "New Name for the Device", placeholder = "--Enter Name Here--", value = "")

    @reactive.Effect
    @reactive.event(input.blink)
    def _():
        """
        Triggers a blink action on the selected device when the 'Blink' button is clicked.

        Helps users with multiple visually identical instruments correlate software names
        with pieces of hardware. 
        """        
        req(input.device())
        device = next((x for x in Device.all if x.sn == input.device()), None)
        device.blink()
