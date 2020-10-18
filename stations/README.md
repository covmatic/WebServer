# How to write **protocol** json files

## JSON structure
To ensure a correct working of the web app, the protocol should be translated in a proper json structure.

We defined a 3 level structure, from the more specific to the less specific:

* Instruction
* Task
* Group

### Instructions

An instruction is a JSON object with this structure:

Key | Value Type | Description | Optional 
--  | -- | -- | :-: 
name | string | This field will be displayed and is an action that the operator has to do| 
isInput | number | This field accept 1/0 value if 1 it means you expect an input from the process | X
notes | list of strings | If it's needed to clarify the action the values of the list are rendered as a bullet list on the web app | X 
rackPosition | string | In the initial filling of rack with patient tube this value represent the tube position in the Rack  | X 

## Tasks

A task is a JSON object with this structure:

| Key | Value Type | Description | Optional 
| --  | -- | -- | :-: 
| name | string | this value sum up the task the operator should do doing instructions| |
| action | can have a value from the below list and tells the UI to query the local server for executing automation ||X
| instructions | List of **Instructions** |  | X
| input | string | if this key is present the UI renders an input form <br> if the value is **barcode** the barcode check are performed <br> if the value is **sender** the value is concatenated with each barcode inserted during the protocol execution | X 
| endpoint | string | if the input is valorized as **barcode** than this key should be valorize as **input/previous_station_type** or **output** and this tells the UI if the barcode check is performed for an input in the process or an output. The **previous_station_type** tells where should be checked the barcode as output process. For patient check use **lis** as previous_station_type. | X 

Each task is a set of instruction that the operator does together and will displayed as unique group. 

**N.B.** For each task it's strongly reccomended that there is only one input instruction or one action, because the value inputed or the action result are stored in the same key-value pair returned by the UI.


## Groups
A group is a JSON object with this structure:

| Key | Value Type | Description | Optional |
| --  | -- | -- | :-: |
| name | string |  |
| tasks | List of **Tasks**

The protocol is a list of groups.

# How to write action in the json files

## For Stations
| Station | URL |
|--|--|
| A | 1 |
|B|2|
|C|3|
|PCR|4|

## For Actions
|Action|URL|
|--|--|
|Setting temperature module|settemp|
| Checking if temperature equals target|checktemp|
|Calibrate Opentrons|calibration|
| Station A Purebase P1000S Pre-incubation|Pre-IncubationV1|
| Station A Purebase P300S pre-incubation|Pre-IncubationV2|
| Station A Purebase P1000S post-incubation|Post-IncubationV1|
| Station A Purebase P300S post-incubation|Post-IncubationV2|
| Station B|Run|
| Station C	|Run|
| PCR|Run|
