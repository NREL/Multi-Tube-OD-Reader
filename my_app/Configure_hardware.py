<<<<<<< HEAD
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
=======
from shiny import module, ui, reactive, render, req
from sampling import connected_device, valid_sn
import u3
from LabJackPython import Close
import time

@module.ui 
def configure_ui():
    return ui.page_fluid(
        ui.h2({"style": "text-align: center;"}, "Configure Hardware"),
        ui.row(
            ui.column(
                6,
                ui.div(
                    ui.output_ui("Select_device"),
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
    def Select_device():
        choices = [app_main.name_for_sn(sn) for sn in valid_sn()]
        return ui.input_select("device", "Select a Device to interact with", choices=choices)

    @reactive.Effect
    @reactive.event(input.set_name)
    def _():
        req(input.new_name() != "")
        d = connected_device(serialNumber=app_main.sn_for_name(input.device()))
        d.setName(input.new_name())
        choices = [app_main.name_for_sn(sn) for sn in valid_sn()]
        ui.update_select("device", label = "Select a Device to interact with", choices = choices)
        ui.update_text("new_name", label = "New Name for the Device", placeholder = "--Enter Name Here--", value = "")
        Close()

    @reactive.Effect
    @reactive.event(input.blink)
    def _():
        sn = app_main.sn_for_name(input.device())
        d = connected_device(sn)
        delay = 0.15 #period between flashes of LED

        c = 0
        while c < 25:
            toggle = c % 2 #cycles between 1 and 0
            d.getFeedback(u3.LED(State = toggle ))   #this is the built-in LED, 0 and 1 are falsy and truthy.
            d.setDOState(16, c % 2 ) # this is for an LED from CIO0 to ground
            d.getFeedback(u3.DAC8(Dac = 0, Value = d.voltageToDACBits(toggle * 2.5, dacNumber = 0))) #converts desired voltage to calibrated bits and sends to dac0
            time.sleep(delay)
            c += 1
        Close()

import app as app_main
>>>>>>> origin/main
