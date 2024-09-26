# Multi-Tube-OD-Reader
### Overview
Our **Multi-Tube-OD-Reader** device is based on the TubeOD reader [published here](https://doi.org/10.3389/fmicb.2021.790576), but with a housing to maximize throughput.

This repository contains the schematics for 3D printing an enclosure, a parts list for constructing, and the code for controlling the 16-tube, in-line optical density monitoring device. This device and software are particularly useful for researchers studying microbes that grow well in Hungate tubes, but are not amenable to growth in microplate readers.

- [Features](#features)
- [Limitations](#limitations)
- [Tutorial](#interacting-with-the-instrument)
- [Installation](#installation)
- [For Developers](#app-structure-mostly-for-developers--troubleshooting)
- [License](#license)

### Features
- **Real-time Monitoring:** View the OD measurements of multiple cultures in real time. Supports multiple, simultaneous, independent experiments.
- **User-Friendly Interface:** Easy-to-use, browser-based GUI for data collection and managing hardware. Install the software, connect the USB cable, connect the power cable and it's ready to go.
- **Calibration-ready:** Supports custom calibration tables to scale optical density readings to your favorite standard instrument. Raw data are always saved. Interpreted data can be saved as an xlsx file and include calibration tables. 
- **Multi-User Safe:** Experiments are spun-off as independent processes that continue even if the app is closed. Unique file naming is enforced to ensure that previous data cannot be overwritten. 
- **High throughput:** Connect as many Multi-Tube-OD-Readers as your incubator can hold. USB splitters and GUI allow identification and control of parallel independent instruments.

[Back to top](#overview)
### Limitations
- The hardware was designed for observing optical densities of *Clostridium thermocellum* growing in glass Hungate tubes. The optical properties of the glassware, medium and organism can interfere with the sensitivity of the instrument, especially at lower optical densities.
- The code works for us. It is not extensively tested and may require some modification on your machine.

[Back to top](#overview)
### Interacting with the Instrument
#### Nomenclature
- A *Device* is the whole unit with 16 Ports in it.
- A *Port* holds and measures one tube. Each Port can operate independently.
- An *Experiment* is a set of Ports & Devices taking measurements. Experiments run in the background indefinitely, until they are shut off in the app by the user or until the computer restarts.
#### Instrument Setup
Initial installation instructions are provided below. For routine use...

**Start the Shiny App** (if necessary) 
```
#from the Multi-Tube-OD-Reader directory
python -m shiny run --reload --launch-browser my_app/app.py 
```
This should open your default web browser and show the user interface.
### User Interface
#### Home: 
- View & interact with ongoing Experiments.
![Image of Home Page with growth curve data showing for an active experiment](/Screenshots/Home%20Page%20with%20active%20experiment.png)

- Safeguards protect from accidentally stopping the run.
![Image of Home Page with a popup confirming user's intention to shut down the run](/Screenshots/Home%20Page%20with%20Stop-Run%20confirmation.png)

#### Start New Run:
- Step 1: Experiment name and measurement interval
![Image of Start New Run page accepting experiment name and time interval inputs](/Screenshots/Start%20New%20Run%20Step%201.png)

- Safeguards to protect from overwriting previous data files.
![Image of Start New Run page warning user that the file name already exists](/Screenshots/Start%20New%20Run%20Invalid%20Name%20Warning.png)

- Step 2: Select device and number of Ports. We named our devices based on the incubators they live in. ![Image of Start New Run page showing options for attached devices and number of available ports](/Screenshots/Start%20New%20Run%20Step%202.png)

- Step 3: Place growth tubes. Ports are automatically assigned based on availability. ![Image of Start New Run page showing instructions on where to place culture tubes](/Screenshots/Start%20New%20Run%20Step%203.png)

- Complete: The User is automatically redirected to the Home Page with the New Experiment added to the list of Active Experiments. ![Image of Home Page with a new experiment added](/Screenshots/Home%20Page%20with%20New%20active%20experiment.png)

#### Configure Hardware:
- Identify and Rename devices. The Blink button makes the indicator LED blink on the device. 
![Image of Configure Hardware page showing options to select a device, make it blink and rename it](/Screenshots/Manage%20Hardware%20Page.png)

#### Calibration: 
Performed mostly offline, no tab for this function
- Prepare reference tubes to several known optical densities. 
- Measure each reference level using each port the Multi-Tube-OD-Reader
- Transform raw Voltage data to log$_{10}$( Voltage ) 
- Fit a line with y = Known data and x = log$_{10}$( Voltage )
- Update the slope & intercept for each port and other relevant data into the `Calibration.tsv` found in the `my_app` directory.

[Back to top](#overview)
### Installation 
#### Hardware
The hardware requires two connections:
1. A USB cable for data transfer to the computer.
	- USB splitters can be used to branch one USB cable from the computer to multiple Devices. This can help reduce the number of cables passing through the incubator.
2. A power supply cable providing up to about 0.5 amps of 5V DC electrical power.
#### Software
The app requires a U3-compatible driver from [LabJack.com](https://support.labjack.com/docs/labjackpython-for-ud-exodriver-u12-windows-mac-lin).
- For Windows: the UD Driver
- Linux macOS: the Exodriver 

All other required packages are either listed in the `requirements.txt` file or provided in this repository. The following instructions are a typical way to install all of them.

**Copy this Repository to the Computer connected to the Device:** 
 ```
 git clone https://github.com/NREL/Multi-Tube-OD-Reader.git
 ```

**Navigate to the Project Directory:**
```
cd Multi-Tube-OD-Reader
```

**Create a Virtual Environment (Optional):**
Windows users may have different strategies for activating a python virtual environment in WSL vs cmd vs PowerShell. PowerShell users see [this answer](https://stackoverflow.com/a/59815372) 
```
python -m venv MTOD
source MTOD/bin/activate 
```

**Install Dependencies:**
```
pip install -r my_app/requirements.txt
```

**Start the Shiny App**
```
#from Multi-Tube-OD-Reader directory
python -m shiny run --reload --launch-browser my_app/app.py 
```

[Back to top](#overview)
### App Structure (mostly for developers & troubleshooting)
The app was written in Python using modules in a three-tier architecture:
1. *A minimal* `timecourse.py` *script*. This script, and the receives a `.csv` file with instructions in the header that describe the measurement parameters. This script controls the Multi-Tube-OD-Reader device throughout the duration of an experiment and feeds raw data into the `.csv` file. This script was designed to be lightweight so multiple parallel-independent instances can run simultaneously without crashing the computer.
2. *Three custom Python classes* `Device`, `Port`, *and* `Experiment` *mirroring their physical counterparts.* Objects of these classes convey data between the GUI, a `config.dat` file, and the instrument. The `config.dat` file stores the status of the instrument and active experiments in case the app closes. Only the `Device` class (and `timecourse.py` script) interact directly with the instrument.
3. *Modules comprising the GUI. Written in Shiny for Python.* This runs a server on localhost. Advanced users may be able to serve the app to remote clients to monitor the data. We simply use remote login to the laptop running the app. The modules on this tier serve several functions:
	1. Convert user parameters to inputs to `timecourse.py` 
	2. Store instrument and app state in `config.dat`
	3. Calculate valid options for user input
	4. Reject or correct invalid user input

[Back to top](#overview)
### License
The hardware and software were built from open source resources. The material in this repository were developed at the National Renewable Energy Laboratory under the Laboratory-Directed Research & Development program. The materials in this repository are subject to the BSD-3-Clause License. 

**No Guarantees:**
- **Accuracy:** We make no representations or warranties about the accuracy, reliability, completeness, or timeliness of the content. The instructions and information provided may contain errors or inaccuracies.
- **Functionality:** We do not guarantee that the hardware or software will function correctly or meet your needs. There may be unforeseen issues or incompatibilities that arise during implementation.
- **Support:** There is no obligation to provide support, maintenance, or updates for the materials provided in this repository.

[Back to top](#overview)
