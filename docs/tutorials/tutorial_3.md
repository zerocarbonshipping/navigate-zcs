<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Tutorial 3

```{button-link} tutorial_3.zip
:color: primary

Download the tutorial 3 files
```

The download holds the folder `tutorial_3` with the empty working files that you copy into your own folder structure during this tutorial. Unzip it where you want to work. An [example solution](#example-solution) is at the bottom of this page.

**Why are you doing this tutorial?**

The purpose of this tutorial is to introduce you to the concept of modularization of the Navigate files. Essentially splitting the instructions into multiple `.inc` files in order to make them more readable and easier to maintain and update. This is especially relevant when working with scenarios, uncertainties, and sensitivities where there are often only a handful of assumptions that are changed while the majority remain the same across all simulations.

**Setting the scene:**

In this tutorial, you will first be introduced to the structure of the simulation environment we use and have designed for working with multiple projects, scenarios, and uncertainties. This will serve as guidance but is not a mandatory structure. Then you will create your own folder structure for this tutorial.

You will then divide the content of Tutorial 2’s DEFINE file up into several smaller `.inc` files and store them in the relevant tutorial folders. In the last part, you will run three simulations with different LSFO prices (baseline: 250 USD/ton, Scenario 170 USD/ton, Scenario 100 USD/ton) and briefly review the results.

**How does it work?**

In this document, you have several action points. Mostly, these action points involve writing instructions to define nodes and their attributes (which you do by writing/copying the Navigate instructions from this document into your own working file) or copying and pasting files between folders and editing them.

You should follow the guide in order as the parts build up on each other.

## Proposed structure of a simulation environment

The way we have structured our simulation environment is as follows:

```
production/
├── 0_includes_global/
├── project_1/
│   ├── 0_includes_local/
│   ├── simulation_1/
│   │   ├── plots/
│   │   └── file_name_1.nav
│   ├── simulation_2/
│   │   ├── plots/
│   │   └── file_name_2.nav
│   └── ...
├── project_2/
│   ├── 0_includes_local/
│   ├── simulation_1/
│   │   ├── plots/
│   │   └── file_name_1.nav
│   ├── simulation_2/
│   │   ├── plots/
│   │   └── file_name_2.nav
│   └── ...
└── ...
```

In the context of the tutorials the folder `project_1` would correspond to `Tutorial_1`, `project_2` would correspond to `Tutorial_2`, etc. The scenarios you will test in this tutorial then corresponds to the folders `simulation_1`, `simulation_2`, etc., under the relevant project or tutorial.

The folder `0_includes_global` is placed in the folder with the `project` folders. This folder contains global assumptions that is not dependent on a project or scenario. The `0_includes_local` under the individual projects contains assumptions that are specific to a project or scenario.

### Build your folder structure

The `tutorial_3` folder will correspond to the `production` folder from the above graphic.

1. In `tutorial_3`, create two new folders:
   1. `0_includes_global`. This will include `.inc` files with all of your base assumptions.
   2. `tutorial_3_scenarios` (this is your "project" in the tree structure)
2. Within the folder `tutorial_3_scenarios`, create four new folders. These are your "simulations" in the tree structure:
   1. `0_includes_local` 
   2. `baseline`. This folder will include the .nav file for the baseline scenario. 
   3. `scenario_170` 
   4. `scenario_100`
4. Within each of the three folders `baseline`, `scenario_170`, and `scenario_100`: Create an empty folder called `plots`

Your folder structure should now look like this:

```
tutorial_3/
├── 0_includes_global/
└── tutorial_3_scenarios/
    ├── 0_includes_local/
    ├── baseline/
    │   ├── plots/
    │   └── (baseline .nav file)
    ├── scenario_170/
    │   └── plots/
    └── scenario_100/
        └── plots/
```

## Split DEFINE content into individual `.inc` files.

In the next step, you will split the content from your tutorial 2 DEFINE file into several smaller files.

You can complete this by opening your finalized DEFINE file from tutorial 2, and paste copies of each individual node, or each section into new .inc files, and save these new files into your `tutorial_3` folder.

Almost all assumptions are going to stay the same as in tutorial 2, and are constant across the three scenarios (baseline, 100, 170) in this tutorial 3. Those assumptions are going to be saved in the `0_includes_global` folder, because we consider them our ‘default’ assumptions.

However, the assumptions (files) about LSFO costs are going to be defined (saved) separately outside of the `0_includes_local` folder, because the different assumptions are unique to their respective scenarios and are therefore considered to be ‘local’ assumptions.

### Recap Tutorial 2

Let’s recap the different files we had under tutorial 2. 
Open your `tutorial_2` folder and files to remind yourself of the contents.

In the `includes` folder we had a:
- `define.inc` file: defining the different assumptions related to the definition of nodes (e.g., about vessel and fuel specifications, emissions related with specific fuels, costs, route details etc.)
- `events.inc` file containing the timesteps of the simulations.
- `tutorial_2.nav` file: including ‘instructions’ on running the simulation and on which files to include (e.g., define and events files)

### New Structure

While all defined nodes and assumptions were in the one DEFINE file, you are now going to split some up and save them into different files.

There are multiple different ways/logics of how you could split the content of the DEFINE file up, but for this tutorial we are using the following structure:

(The order of the list is approximately aligned with the order the nodes/assumptions appear in the DEFINE file).

#### `.nav` files:
1.	`baseline.nav`
2.	`scenario_100.nav`
3.	`scenario_170.nav`
#### `.inc` files (0_includes_global):
1.	`model_definition.inc`
2.	`fleet_bulk.inc`
3.	`fleet_container.inc`
4.	`fleet_uptake.inc`
5.	`container_ice_oil.inc`
6.	`container_ice_methane.inc`
7.	`bulk_ice_methanol.inc`
8.	`bulk_ice_ammonia.inc`
9.	`tanks.inc`
10.	`route.inc`
11.	`port.inc`
12.	`producer.inc`
13.	`producer_uptake.inc`
14.	`plant.inc`
15.	`fuel.inc`
16.	`emissions.inc`
17.	`process.inc`
18.	`feedstock.inc`
19.	`region.inc`
20.	`source.inc`
21.	`report.inc`
22.	`plot.inc`
23.	`time_steps_yearly.inc`

Each section in the list represents a separate `.inc` file in the new file structure.

We have taken the liberty of creating empty working files for you in the folder `tutorial_3` from the download at the top of this page that you can copy into your newly constructed simulation environment. The `.inc` files should be copied into `0_includes_global` subfolders and the `.nav` files should be placed in the respective scenario folders.

### DEFINE File: General Nodes

1. Open these files:
   - From folder ‘tutorial_3/0_includes_global:
      - `model_definition.inc`
   - From the folder `tutorial_2`:
      - `define.inc` (T2DEF)

2. Copy the relevant section from T2DEF into the corresponding empty file.
3. Copy the node `ModelDefinition` into the file `model_definition.inc`.

### DEFINE File: Definition of the Fleets

Open your Tutorial 2 `define.inc` file and copy the depicted nodes into their respective `.inc` file.

#### `fleet_bulk.inc`

1. Copy the relevant section from T2DEF into the empty file.
2. Remove the attribute definitions `InterFuelSensitivity` and `IntraFuelSensitivity` from the node definition (they will be set for all fleets at once in `fleet_uptake.inc`).

```python
Fleet "bulk_fleet" {	
   Vessels = [Vessel("bulk_ice_methanol"), Vessel("bulk_ice_ammonia")] 	
   InitialVessels = 100
   TradeGrowth = 0.05
}
```

#### `fleet_container.inc`

1. Copy the relevant section from T2DEF into the empty file.
2. Remove the attribute definitions `InterFuelSensitivity` and `IntraFuelSensitivity` from the node definition (they will be set for all fleets at once in `fleet_uptake.inc`).

```python
Fleet "container_fleet" {	
   Vessels = [Vessel("container_ice_oil"), Vessel("container_ice_methane")] 	
   InitialVessels = 100
   TradeGrowth = 0.05
}
```

#### `fleet_uptake.inc`

1. Assign the attributes `InterFuelSensitivity` and `IntraFuelSensitivity` to all defined nodes of the type `Fleet`. 
2. The star `*` is a ‘wildcard’. So, when we define the node `Fleet "*"` the listed attributes under it will apply to any node that has the node-type `Fleet`.
3. A value of `0.5` is an odds ratio: a fuel or technology whose levelized cost of transport (LCOT) is 10% higher receives half the odds of an otherwise identical option (lower cost is better, so use a value below `1`).

```python
Fleet "*" {	
   InterFuelSensitivity = 0.5
   IntraFuelSensitivity = 0.5
}
```

### DEFINE File: Definition of the Vessels

1. Create the listed files in your Tutorial 3 `0_includes_global` folder.
2. Open these files:
   - From folder `tutorial_3/0_includes_global`:
     - `container_ice_oil.inc`
     - `container_ice_methane.inc`
     - `bulk_ice_methanol.inc`
     - `bulk_ice_ammonia.inc`
   - From the folder `tutorial_2`: 
      - `define.inc` (T2DEF)
3. Copy the relevant section from T2DEF into the corresponding empty file. All nodes, Vessel, Powersystem and converters should be copied into the corresponding file. E.g. all nodes under Bi) in your T2DEF file should be copied and pasted into the file “container_ice_oil”

### DEFINE File: General Specifications for Vessels

1. Create the listed files in your Tutorial 3 `0_includes_global` folder.
2. Open these files:
   - From folder `tutorial_3/0_includes_global`:
     - `route.inc`
     - `tanks.inc`
     - `port.inc`
   - From the folder `tutorial_2`: 
      - `define.inc` (T2DEF)
3. Copy the relevant section from T2DEF into the corresponding empty file. 
   - For the `route.inc` file, copy and paste the node `Route "route"`. For port copy node `"port"` and pace in file `"port"` in `0_include_global`.
   - For the file `tanks.inc` include all tank nodes: `Tank("main_oil")`, `Tank("pilot_oil")`, `Tank("main_methane")`, `Tank("main_methanol")`, and `Tank("main_ammonia")`.

### DEFINE File: Definition of all Fuels

1. Create the listed files in your Tutorial 3 `0_includes_global` folder.
2. Open these files:
   - From folder ‘tutorial_3/0_includes_global’:
     - `Fuel.inc`
     - `Process.inc`
     - `Feedstock.inc`
   -	From the folder `tutorial_2`: 
     - `define.inc` (T2DEF) 
3. For each of the 3 mentioned files, perform the following action points, resulting in files that contain each of the depicted nodes of code. Remember to save before running any code or closing any files.
4. Open your Tutorial 2 `define.inc` file and copy the depicted nodes into their respective .inc file:

#### `fuel.inc`

1. Copy the relevant section from T2DEF into the empty file:
   - `Fuel "heavy_fuel_oil"`
   - `Fuel "methane_electro"`
   - `Fuel "methanol_bio"`
   - `Fuel "ammonia_blue"`

```python
Fuel "heavy_fuel_oil" {
	FuelType = OIL
	
	LowerHeatingValue = 41.2
	MassDensity = 0.9
	
	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}

Fuel "methane_electro" { 
	FuelType = METHANE
	
	LowerHeatingValue = 50.0  
	MassDensity = 0.43
	
	set_ttw("carbon_dioxide", 2.75)
}


Fuel "methanol_bio" {
	FuelType = METHANOL
	
	LowerHeatingValue = 19.9
	MassDensity = 0.791
	
	set_ttw("carbon_dioxide", 1.38)
}

Fuel "ammonia_blue" {
	FuelType = AMMONIA
	
	LowerHeatingValue = 18.8
	MassDensity = 0.623
}
```

#### 'emissions.inc'

1. Copy the relevant section from T2DEF into the empty file.
    - `Emission "carbon_dioxide"`
    - `Emission "methane"`
    - `Emission "nitrous_oxide"`

```python
Emission "carbon_dioxide" {
	GlobalWarmingPotential = 1
}

Emission "methane" {
	GlobalWarmingPotential = 25
}

Emission "nitrous_oxide" {
	GlobalWarmingPotential = 273
}
```

#### `process.inc`

1. Copy the relevant section from T2DEF into the empty file.
   - `Process "methane_liquefaction_electro"`
   - `Process "methane_synthesis_electro"`
   - `Process "methanol_synthesis_bio_gasification"`
   - `Process "haber_bosch_ccs_integrated_blue"`
   - `Process "nitrogen_air_seperation"`

```python
Process "methane_liquefaction_electro" {  
   Feeds = [Process("methane_synthesis_electro")]
   Conversions = [1]
}

Process "methane_synthesis_electro" {  
   Feeds = [Feedstock("demineralized_water"), Feedstock("carbon_dioxide_biogenic")]
   Conversions = [4.5, 2.75]  
}

Process "methanol_synthesis_bio_gasification" {
   Feeds = [Feedstock("organic_wet_waste"), Feedstock("dry_wood_biomass")]
   Conversions = [1.21, 1.21]
}

Process "haber_bosch_ccs_integrated_blue" {	
   Feeds = [Process("nitrogen_air_seperation"), Feedstock("natural_gas")]	
   Conversions = [0.64, 0.822]						
}

Process "nitrogen_air_seperation" {
}
```

#### `feedstock.inc`

1. Copy the relevant section from T2DEF into the empty file.
   - `Feedstock "demineralized_water"`
   - `Feedstock "carbon_dioxide_biogenic"`
   - `Feedstock "organic_wet_waste"`
   - `Feedstock "dry_wood_biomass"`
   - `Feedstock "natural_gas"`

```python
Feedstock "demineralized_water" {	
}

Feedstock "carbon_dioxide_biogenic" {
}

Feedstock "organic_wet_waste" {
}

Feedstock "dry_wood_biomass" {
}

Feedstock "natural_gas" {
}
```

### DEFINE File: Definition of `Plant` Nodes and `Region`

1. Create the listed files in your Tutorial 3 `0_includes_global` folder.
2. Open these files:
   - From folder `tutorial_3/0_includes_global`:
     - `plant.inc`
     - `source.inc`
     - `region.inc`
   -	From the folder `tutorial_2`: 
     - `define.inc` (T2DEF)
3. Copy the relevant section from T2DEF into the corresponding empty file.
Follow the principle of Fuels, copy the Plant nodes for every fuel and place them into the file plant.inc in `0_includes_global`. Copy the node `“region”` into the `region.inc` file. Copy the nodes Source `"renewable"` and `"grid"` into the file `source.inc`.

### DEFINE File: Definition of `Producer` and `producer_uptake`

1. Create the listed files in your Tutorial 3 `0_includes_global` folder.
2. For producer, copy the node Producer `"engineering_procurement_construction"` and past into file `producer.inc` in `0_includes_global`
This assigns the attribute `"engineering_procurement_construction"`   
And the decision sensitivities to all fuel production plants.

```python
Producer "engineering_procurement_construction" {
    Plants = [Plant("plant_methane_electro"),
              Plant("plant_methanol_bio_gasification"),
              Plant("plant_ammonia_blue")]
    MaximumDevelopment = 10
    FuelDemandSensitivity = 1.5
    FuelCostSensitivity = 0.5
}
```

`FuelDemandSensitivity = 1.5` favours the fuel pathways with the largest expected demand (a 10% higher demand gives 1.5x the odds), while `FuelCostSensitivity = 0.5` favours the cheaper plants within a pathway (a 10% higher levelized cost of fuel halves the odds).

3. The decision sensitivities are now set directly on the `Producer`, so the `producer_uptake.inc` file is left empty — there are no separate uptake nodes to define.

### DEFINE File: Definition of `Plot`

The `Plot` node defines which output plots Navigate produces and where they are saved. Navigate only generates plots when at least one `Plot` node is defined.

1. Open the file `plot.inc` in your `0_includes_global` folder.
2. Define a node `"plots"` with the node type `Plot`.
3. Set the `Directory` attribute to `"./plots/"`. This is the `plots` subfolder you created in each scenario folder; the path is relative to the `.nav` file being run. Navigate creates the folder if it does not already exist.
4. Use the `add_plot(...)` command once per plot you want produced.

```python
Plot "plots" {
    Directory = "./plots/"

    add_plot("global_emission_absolute")
    add_plot("global_fuel_consumed")
    add_plot("plant_production_cost")
    add_plot("port_bunker_price")
}
```

Because the same plots are produced for every scenario, `plot.inc` lives in `0_includes_global` and is included by each scenario's `.nav` file (see the next section).


## Create `.nav` file for Baseline Scenario

### Recap Tutorial 2

Let’s recap what the finalised `tutorial_2.nav` file looked like in tutorial 2. The DEFINE section includes only one file, the `define.inc` file.

```python
# This is the .nav file for Tutorial 2. It is the same as Tutorial 1.
# You should just make sure that your define and events files are correctly named
# and are located in the tutorial_2/includes folder.

# Definition of the DEFINE section
DEFINE {
    Include "./includes/define.inc"
}

# Definition of the EVENTS section
EVENTS {
    Include "./includes/events.inc"
}
```

The EVENTS section includes only one file, the events.inc file.

### Compare and Create a new `baseline.nav` file

For this tutorial 3, you have split the DEFINE file into smaller components. The EVENTS file contains the same but has been renamed to a more informative name describing what it contains.

In order to run the baseline scenario in the model, you also need to modify the `.nav` file with the “instructions” on what files to include in the simulation.

As we spread out the assumptions across many different files, all of them need to be included in tutorial 3’s `.nav` file.


1. Open the folder `\tutorial_3\nav_files`.
2. Copy the empty file `baseline.nav` and paste it into your personal folder `\tutorial_3\tutorial_3_scenarios\baseline`, so you can edit it.
3. **DEFINE section:** Write prompts to include all the files that you just created using the code on the right.
For better overview, group them into categories like you can see on the right side, and annotate them with comments. 

```python
DEFINE {

    # model definition
    Include "../../0_includes_global/model_definition.inc"

    # fleets
    Include "../../0_includes_global/fleet_container.inc"
    Include "../../0_includes_global/fleet_bulk.inc"
    Include "../../0_includes_global/fleet_uptake.inc"

    # vessels
    Include "../../0_includes_global/container_ice_oil.inc"
    Include "../../0_includes_global/container_ice_methane.inc"
    Include "../../0_includes_global/bulk_ice_methanol.inc"
    Include "../../0_includes_global/bulk_ice_ammonia.inc"
    Include "../../0_includes_global/tanks.inc"

    # route
    Include "../../0_includes_global/route.inc"

    # port
    Include "../../0_includes_global/port.inc"

    # fuels
    Include "../../0_includes_global/plant.inc"
    Include "../../0_includes_global/fuel.inc"
    Include "../../0_includes_global/process.inc"
    Include "../../0_includes_global/feedstock.inc"

    # producer
    Include "../../0_includes_global/producer.inc"
    Include "../../0_includes_global/producer_uptake.inc"
    Include "../../0_includes_global/source.inc"

    # costs and emissions of fuels
    Include "../../0_includes_global/region.inc"
    Include "../../0_includes_global/emissions.inc"

    # plots
    Include "../../0_includes_global/plot.inc"
}
```

4. **EVENTS section:** Include the `.inc` file that was prepared for you.

```python
EVENTS {
    # time steps
    Include "../../0_includes_global/time_steps_yearly.inc"
}
```

## Run the Baseline Scenario

Open the terminal and change directory to where the tutorial simulation files are. Once positioned in the folder use the following command to run Navigate:

```bash
# Example cd workflow (linux)
cd tutorial_3/tutorial_3_scenarios/baseline/

# Run Navigate
navigate baseline.nav
```

## Create Sensitivities: HFO Price

Next, you are going to run a sensitivity analysis on the price of HFO. This means that you are going to create several different scenarios which **differ only in the price of LSFO while other assumptions stay constant** across all scenarios. 

Comparing e.g., the projected fuel mix over time, can give you insights about the impact that the price of HFO has on the shipping industry and on the transition. For example, if all scenarios lead to very similar projected fuel mixes, we might conclude that the price of HFO has a very small influence on the overall transition, and that other factors, like bio-methane or vessel availability might be the driving factors in the transition.

However, if the scenarios lead to very different fuel mix projections, this is an indicator that the HFO price is very important in influencing the transition. Implications of this include that it is very important to be confident in the values we assume to be the ‘true’ HFO prices today (and in the future). This is because the results of our simulations might be skewed/wrong, if our assumed HFO prices are inaccurate, and might ultimately lead us to drawing the wrong conclusions. 

You are going to create two additional scenarios with different HFO costs – a low (ca. 100 USD/ton) and a medium (ca. 170 USD/ton). In the ‘scenario 100’, HFO will be the cheapest fuel available, in the ‘scenario 170’ LSFO price will be cheaper than some fuels but more expensive than others. In the baseline scenario, HFO is the most expensive fuel.


### Create an `.inc` file for Scenario 100: Lowest Cost

You will create an `.inc`-file to define the HFO price for Scenario 100, and you will create a `.nav` file for the scenario. 
The structure will be the exact same as in the input file you already created for the baseline scenario, `cost_emissions_lsfo.inc`.

1. Open the folder `\tutorial_3\scenario_files`.
2. Copy the file `scenario_100.inc` and paste it into your personal folder: `\tutorial_3\tutorial_3_scenarios\0_includes_local`.
3. Assign a price for heavy fuel oil of 100 USD/ton to the port node `"port"`.

```python
Port "port" {	
    set_bunker_price_overwrite("heavy_fuel_oil", 100) 
}
```

### Create a `.nav` file for Scenario 100: Lowest Cost

1. Open the folder `\tutorial_3\nav_files`
2. Copy the empty file `scenario_100.nav` and paste it into your personal folder `\tutorials\tutorial_3\tutorial_3_scenarios\scenario_100`, so you can edit it.
3. Copy the entire content of the `baseline.nav` file, and paste it into the file `scenario_100.nav`. 
4. Right before the end of the definition of DEFINE, add a line that includes the new input file you just created, `scenario_100.inc`.
The code is marked with a red box in the example.
5. Add a comment explaining the new line for your own overview.
You might notice that you had already defined the cost for HFO in the file `port.inc` which is still included in the `.nav` file here.
Any new input files added below a previously included file will overwrite existing values, e.g. in this case related to the cost of HFO.
Hence, when the model is run now, the vales for cost and emissions related to HFO will 
be those defined in `scenario_100.inc`.

```python
DEFINE {

    # general nodes
    Include "../../0_includes_global/model_definition.inc"

    # fleets
    Include "../../0_includes_global/fleet_container.inc"
    Include "../../0_includes_global/fleet_bulk.inc"
    Include "../../0_includes_global/fleet_uptake.inc"

    # vessels
    Include "../../0_includes_global/container_ice_oil.inc"
    Include "../../0_includes_global/container_ice_methane.inc"
    Include "../../0_includes_global/bulk_ice_methanol.inc"
    Include "../../0_includes_global/bulk_ice_ammonia.inc"
    Include "../../0_includes_global/tanks.inc"

    # route
    Include "../../0_includes_global/route.inc"

    # port
    Include "../../0_includes_global/port.inc"

    # fuels
    Include "../../0_includes_global/plant.inc"
    Include "../../0_includes_global/fuel.inc"
    Include "../../0_includes_global/process.inc"
    Include "../../0_includes_global/feedstock.inc"

    # producer
    Include "../../0_includes_global/producer.inc"
    Include "../../0_includes_global/producer_uptake.inc"
    Include "../../0_includes_global/source.inc"

    # costs and emissions of fuels
    Include "../../0_includes_global/region.inc"
    Include "../../0_includes_global/emissions.inc"

    # plots
    Include "../../0_includes_global/plot.inc"

    # testing sensitivity to lower HFO cost
    Include "../0_includes_local/scenario_100.inc"
}
```

6. The definition of EVENTS can stay the same. Save your edits.

#### Run Scenario 100 in Navigate

Open the terminal and change directory to where the tutorial simulation files are. Once positioned in the directory, use the following command to run Navigate:

```bash
navigate .\scenario_100.nav
```

This will run the Navigate simulation using the instructions in the `tutorial_file_name.nav` file.

Did you get an error message?

```
FileNotFoundError: Error in DEFINE file, line XX: Include file '../0_includes_local/scenario_100.inc' not found.
```

#### Moving on

The files baseline.nav and scenario_100.nav are almost identical, because all assumptions except the assumption about the HFO price are the same.
Hence, the general structure can stay the same, and the same files from 0_includes_global need to be included.

The reason for why Navigate is not running is because of the difference in folder levels that are between the respective .nav files and the folders containing the relevant .inc input files.
From the location of `baseline.nav`, it is 2 levels ‘up’ to get to the folder `0_includes_global` which includes the relevant assumption files. That is why there is a ‘double dash’ (../../) in most of the `Include` prompts. 

However, from the location of `scenario_100.nav`, it is 1 level 'up' to the folder 0_includes_local, which includes the relevant input file `scenario_100.inc`. This needs to be reflected in the code by single 'dash', i.e. you need to remove one `../` in the description of the file location.

#### Referencing local assumptions in `Scenario_100.nav`

1. Correct the file so it can find the input files by removing one dash "../" in front of the file location of `scenario_100.inc`.
   - I.e., change `Include "../../0_includes_global/*.inc"`
   - to `Include "../0_includes_local/*.inc"`
2. Save your edits and run the scenario again.

### Create a `.nav` file for Scenario 170: Medium Cost

1. Open the folder `tutorial_3\scenario_files`
2. Copy the empty file `scenario_170.inc` and paste it into your personal folder `\tutorial_3_scenarios\0_includes_local`, so you can edit it.
3. Assign a price for heavy fuel oil of 170 USD/ton to the port node `"port"`.

```python
Port "port" {
    set_bunker_price_overwrite("heavy_fuel_oil", 170) 
}
```

4. Open the folder `tutorial_3\nav_files`
5. Copy the empty file `scenario_170.nav` and paste it into your personal folder `\tutorial_3_scenarios\scenario_170`, so you can edit it.
6. Right before the end of the definition of DEFINE, edit the last line and change it from saying `"scenario_100.inc"` to `"scenario_170.inc"`.

```python
DEFINE {

    # general nodes
    Include "../../0_includes_global/model_definition.inc"

    # fleets
    Include "../../0_includes_global/fleet_container.inc"
    Include "../../0_includes_global/fleet_bulk.inc"
    Include "../../0_includes_global/fleet_uptake.inc"

    # vessels
    Include "../../0_includes_global/container_ice_oil.inc"
    Include "../../0_includes_global/container_ice_methane.inc"
    Include "../../0_includes_global/bulk_ice_methanol.inc"
    Include "../../0_includes_global/bulk_ice_ammonia.inc"
    Include "../../0_includes_global/tanks.inc"

    # route
    Include "../../0_includes_global/route.inc"

    # port
    Include "../../0_includes_global/port.inc"

    # fuels
    Include "../../0_includes_global/plant.inc"
    Include "../../0_includes_global/fuel.inc"
    Include "../../0_includes_global/process.inc"
    Include "../../0_includes_global/feedstock.inc"

    # producer
    Include "../../0_includes_global/producer.inc"
    Include "../../0_includes_global/producer_uptake.inc"
    Include "../../0_includes_global/source.inc"

    # costs and emissions of fuels
    Include "../../0_includes_global/region.inc"
    Include "../../0_includes_global/emissions.inc"

    # plots
    Include "../../0_includes_global/plot.inc"

    # testing sensitivity to lower HFO cost
    Include "../0_includes_local/scenario_170.inc"
}
```

7. Save your edits, cd into the folder `scenario_170` and run:
```bash
navigate .\scenario_170.nav
```

## Run the scenarios and compare them with baseline

Open the plot folders for the baseline, scenario 100 and scenario 170 next to each other. Review some of the plots and compare them across scenarios.

### Making a report for further analysis in Excel

If you want to extract results from Navigate into excel to create your own graph or make additional analysis you can have Navigate extract a report, including all the parameters you need.

1. Open the `report.inc` from your 0_includes_global folder.
2. Create a `Report` node named `report`, and set its `Directory` attribute to `"./plots/"` so the Excel report is saved in the same subfolder as the plots.
3. Add the results from the simulation that you would like exported into an excel sheet, from where it can be used for analysis in other programs than Navigate. 
   - **Port:** First, we would like to extract bunker price and WTT intensity.
   - **Fleet:** The fleet properties extracted is the emissions and total energy consumption from the fleets.
   - **Global:** Here properties of emissions, energy consumption, and installed engine power is extracted at a global level (so across fleets).

```python
Report "report" {	

	# export the report to the same "plots" subfolder as the plots.
	Directory = "./plots/"

	# port
	add_port_property("*", BunkerIntensityPrice)    	        # USD/GJ
	add_port_property("*", BunkerIntensityTotalEquivalentWtt)	# kg/GJ
		
	# fleet
	add_fleet_property("*", TotalEquivalentWtt)		# ton/year
	add_fleet_property("*", TotalEquivalentTtw)		# ton/year
	add_fleet_property("*", TotalEquivalentWtw)		# ton/year
	add_fleet_property("*", TotalConsumedEnergy)    # GJ/year

	# global
	add_property(TotalEquivalentWtt)				# ton/year
	add_property(TotalEquivalentTtw)				# ton/year
	add_property(TotalEquivalentWtw)				# ton/year
	add_property(TotalConsumedEnergy)				# GJ/year
	add_property(ConsumedEnergy)					# GJ/year
	add_property(InstalledPower)					# MW	
}
```
4. In each scenario `.nav` file (`baseline.nav`, `scenario_100.nav` and `scenario_170.nav`), inside the `DEFINE` block add the line `Include "../../0_includes_global/report.inc"`, placing it just before the `plot.inc` include. If you only add it to `baseline.nav`, the other two scenarios will run but produce no Excel report.
5. Run the Baseline scenario in Navigate

## Example solution

One way to complete this tutorial. Each box holds one file, at its path inside the `tutorial_3` folder.

:::{dropdown} tutorial_3_scenarios/baseline/baseline.nav
```python
# baseline.nav file for tutorial 3

DEFINE {	
				
	### model definition and general conditions
	Include "../../0_includes_global/model_definition.inc"
	
	# fleets
	Include "../../0_includes_global/fleet_bulk.inc"
	Include "../../0_includes_global/fleet_container.inc"
	Include "../../0_includes_global/fleet_uptake.inc"
	
	# vessels
	Include "../../0_includes_global/container_ice_oil.inc"
	Include "../../0_includes_global/container_ice_methane.inc"
	Include "../../0_includes_global/bulk_ice_methanol.inc"
	Include "../../0_includes_global/bulk_ice_ammonia.inc"
	Include "../../0_includes_global/tanks.inc"

	# route
	Include "../../0_includes_global/route.inc"
	
	# port
	Include "../../0_includes_global/port.inc"
	
	# fuels
	Include "../../0_includes_global/plant.inc"
	Include "../../0_includes_global/fuel.inc"
	Include "../../0_includes_global/process.inc"
	Include "../../0_includes_global/feedstock.inc"

	
	# costs and emission of fuels
	Include "../../0_includes_global/source.inc"
	Include "../../0_includes_global/region.inc"
    Include "../../0_includes_global/emissions.inc"

	# producer
	Include "../../0_includes_global/producer.inc"
	Include "../../0_includes_global/producer_uptake.inc"
	
	# report
	Include "../../0_includes_global/report.inc"

	# plots
	Include "../../0_includes_global/plot.inc"
}


EVENTS {					
	# engine availability
	
	# fuels available
	
	# time steps
	Include "../../0_includes_global/time_steps_yearly.inc"
}
```
:::

:::{dropdown} tutorial_3_scenarios/scenario_100/scenario_100.nav
```python
# scenario_100.nav file for tutorial 3

DEFINE {	
				
	### model definition and general conditions
	Include "../../0_includes_global/model_definition.inc"
	
	# fleets
	Include "../../0_includes_global/fleet_bulk.inc"
	Include "../../0_includes_global/fleet_container.inc"
	Include "../../0_includes_global/fleet_uptake.inc"
	
	# vessels
	Include "../../0_includes_global/container_ice_oil.inc"
	Include "../../0_includes_global/container_ice_methane.inc"
	Include "../../0_includes_global/bulk_ice_methanol.inc"
	Include "../../0_includes_global/bulk_ice_ammonia.inc"
	Include "../../0_includes_global/tanks.inc"

	# route
	Include "../../0_includes_global/route.inc"
	
	# port
	Include "../../0_includes_global/port.inc"
	
	# fuels
	Include "../../0_includes_global/plant.inc"
	Include "../../0_includes_global/fuel.inc"
	Include "../../0_includes_global/process.inc"
	Include "../../0_includes_global/feedstock.inc"
	
	
	# costs and emission of fuels
	Include "../../0_includes_global/source.inc"
	Include "../../0_includes_global/region.inc"
    Include "../../0_includes_global/emissions.inc"

	# producer
	Include "../../0_includes_global/producer.inc"
	Include "../../0_includes_global/producer_uptake.inc"

	# report
	Include "../../0_includes_global/report.inc"

	# plots
	Include "../../0_includes_global/plot.inc"


	Include "../0_includes_local/scenario_100.inc"
}


EVENTS {					
	# engine availability
	
	# fuels available
	
	# time steps
	Include "../../0_includes_global/time_steps_yearly.inc"
}
```
:::

:::{dropdown} tutorial_3_scenarios/scenario_170/scenario_170.nav
```python
# scenario_170.nav file for tutorial 3

DEFINE {	
				
	### model definition and general conditions
	Include "../../0_includes_global/model_definition.inc"
	
	# fleets
	Include "../../0_includes_global/fleet_bulk.inc"
	Include "../../0_includes_global/fleet_container.inc"
	Include "../../0_includes_global/fleet_uptake.inc"
	
	# vessels
	Include "../../0_includes_global/container_ice_oil.inc"
	Include "../../0_includes_global/container_ice_methane.inc"
	Include "../../0_includes_global/bulk_ice_methanol.inc"
	Include "../../0_includes_global/bulk_ice_ammonia.inc"
	Include "../../0_includes_global/tanks.inc"

	# route
	Include "../../0_includes_global/route.inc"
	
	# port
	Include "../../0_includes_global/port.inc"
	
	# fuels
	Include "../../0_includes_global/plant.inc"
	Include "../../0_includes_global/fuel.inc"
	Include "../../0_includes_global/process.inc"
	Include "../../0_includes_global/feedstock.inc"
	
	# costs and emission of fuels
	Include "../../0_includes_global/source.inc"
	Include "../../0_includes_global/region.inc"
    Include "../../0_includes_global/emissions.inc"

	# producer
	Include "../../0_includes_global/producer.inc"
	Include "../../0_includes_global/producer_uptake.inc"

	# report
	Include "../../0_includes_global/report.inc"

	# plots
	Include "../../0_includes_global/plot.inc"

	Include "../0_includes_local/scenario_170.inc"
}


EVENTS {					
	# engine availability
	
	# fuels available
	
	# time steps
	Include "../../0_includes_global/time_steps_yearly.inc"
}
```
:::

:::{dropdown} tutorial_3_scenarios/0_includes_local/scenario_100.inc
```python
# Definition of port with alternative bunkering price
Port "port" {
	set_bunker_price_overwrite("heavy_fuel_oil", 100)
}
```
:::

:::{dropdown} tutorial_3_scenarios/0_includes_local/scenario_170.inc
```python
# Definition of port with alternative bunkering price
Port "port" {
	set_bunker_price_overwrite("heavy_fuel_oil", 170)
}
```
:::

:::{dropdown} 0_includes_global/bulk_ice_ammonia.inc
```python
# The ammonia powered bulk vessel incl. powersystem and converters

Vessel "bulk_ice_ammonia" {
	PowerSystem = PowerSystem("ice_ammonia") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("pilot_oil"), Tank("main_ammonia")]	
	PropulsionLoad = 10
}

PowerSystem "ice_ammonia" {
	Propulsion = Converter("propulsion_ice_ammonia")
	Electrical = Converter("electrical_ice_ammonia")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_ammonia" { 
	PowerCapacity = 50 			  
	MainFuelTypes = AMMONIA
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05	
	Efficiency = 0.51
}

Converter "electrical_ice_ammonia" { 
	PowerCapacity = 10 
	MainFuelTypes = AMMONIA 
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
}
```
:::

:::{dropdown} 0_includes_global/bulk_ice_methanol.inc
```python
# The methanol powered bulk vessel incl. powersystem and converters

Vessel "bulk_ice_methanol" {
	PowerSystem = PowerSystem("ice_methanol") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("pilot_oil"), Tank("main_methanol")] 
	PropulsionLoad = 10
}

PowerSystem "ice_methanol" {
	Propulsion = Converter("propulsion_ice_methanol")
	Electrical = Converter("electrical_ice_methanol")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_methanol" { 
	PowerCapacity = 50 			  
	MainFuelTypes = METHANOL 
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05	
	Efficiency = 0.51
}

Converter "electrical_ice_methanol" { 
	PowerCapacity = 10 
	MainFuelTypes = METHANOL
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
}
```
:::

:::{dropdown} 0_includes_global/container_ice_methane.inc
```python
# The methane powered container vessel incl. powersystem and converters

Vessel "container_ice_methane" {
	PowerSystem = PowerSystem("ice_methane") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("pilot_oil"), Tank("main_methane")]
	PropulsionLoad = 10
}

PowerSystem "ice_methane" {
	Propulsion = Converter("propulsion_ice_methane")
	Electrical = Converter("electrical_ice_methane")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_methane" { 
	PowerCapacity = 50 			  
	MainFuelTypes = METHANE 	
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.51
	set_slip_fraction(METHANE, 0.01)
}

Converter "electrical_ice_methane" { 
	PowerCapacity = 10 
	MainFuelTypes = METHANE
	PilotFuelTypes = OIL
	MinimumPilotFuel = 0.05
	Efficiency = 0.5
	set_slip_fraction(METHANE, 0.01)
}
```
:::

:::{dropdown} 0_includes_global/container_ice_oil.inc
```python
# The fuel oil powered container vessel incl. powersystem and converters

Vessel "container_ice_oil" {
	PowerSystem = PowerSystem("ice_oil") 	
	Route = Route("route") 		
	NominalCapacity = 8000
	Tanks = [Tank("main_oil")]						
	PropulsionLoad = 10
}

PowerSystem "ice_oil" {
	Propulsion = Converter("propulsion_ice_oil")
	Electrical = Converter("electrical_ice_oil")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_oil" { 
	PowerCapacity = 50 			  
	MainFuelTypes = OIL
	Efficiency = 0.51
}

Converter "electrical_ice_oil" { 
	PowerCapacity = 10 
	MainFuelTypes = OIL
	Efficiency = 0.5
}
 
Converter "heat_boiler_oil" {
	PowerCapacity = 5  
	MainFuelTypes = OIL
	Efficiency = 0.5
}
```
:::

:::{dropdown} 0_includes_global/emissions.inc
```python
Emission "carbon_dioxide" {
	GlobalWarmingPotential = 1
}

Emission "methane" {
	GlobalWarmingPotential = 25
}

Emission "nitrous_oxide" {
	GlobalWarmingPotential = 273
}
```
:::

:::{dropdown} 0_includes_global/feedstock.inc
```python
# Definition of feedstocks

# Definition of "demineralized_water"
Feedstock "demineralized_water" {	
}

# Definition of "carbon_dioxide_biogenic" 
Feedstock "carbon_dioxide_biogenic" {
}

# Definition of "organic_wet_waste"
Feedstock "organic_wet_waste" {
}

# Definition of "dry_wood_biomass"
Feedstock "dry_wood_biomass" {
}

# Definition of feedstock "natural_gas"
Feedstock "natural_gas" {
}
```
:::

:::{dropdown} 0_includes_global/fleet_bulk.inc
```python
# Definition of bulk fleet

Fleet "bulk_fleet" {	
	Vessels = [Vessel("bulk_ice_methanol"), Vessel("bulk_ice_ammonia")] 	
	InitialVessels = 100
	TradeGrowth = 0.05
}
```
:::

:::{dropdown} 0_includes_global/fleet_container.inc
```python
# Definition of container fleet

Fleet "container_fleet" {	
	Vessels = [Vessel("container_ice_oil"), Vessel("container_ice_methane")] 	
	InitialVessels = 100 
	TradeGrowth = 0.05
}
```
:::

:::{dropdown} 0_includes_global/fleet_uptake.inc
```python
# Definition of fleets' decision sensitivities (odds ratios; LCOT is lower-is-better, so below 1)

Fleet "*" {
	InterFuelSensitivity = 0.5
	IntraFuelSensitivity = 0.5
}
```
:::

:::{dropdown} 0_includes_global/fuel.inc
```python
# Definition of fuels


# Definition of "heavy_fuel_oil"
Fuel "heavy_fuel_oil" {
	FuelType = OIL
	LiquidMarket = TRUE

	LowerHeatingValue = 41.2
	MassDensity = 0.9
	
	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}


# Definition of "methane_electro" 
Fuel "methane_electro" {
	FuelType = METHANE

	LowerHeatingValue = 50.0
	MassDensity = 0.43
	
	set_ttw("carbon_dioxide", 2.75)
}

# Definition of "methanol_bio" 
Fuel "methanol_bio" {
	FuelType = METHANOL

	LowerHeatingValue = 19.9
	MassDensity = 0.791
	
	set_ttw("carbon_dioxide", 1.38)
}

# Definition of "ammonia_blue" 
Fuel "ammonia_blue" {
	FuelType = AMMONIA

	LowerHeatingValue = 18.8
	MassDensity = 0.623
}
```
:::

:::{dropdown} 0_includes_global/model_definition.inc
```python
# The model definition.

ModelDefinition {
	StartDate = "01/01/2025"
}
```
:::

:::{dropdown} 0_includes_global/plant.inc
```python
# Definition of fuel production plants


# e-methane -------------------------------------------------------
Plant "plant_methane_electro" {     #e-methane plant difinition
	Fuel = Fuel("methane_electro")      #difinition of fuel: e-methane with CCS from point source
	Process = Process("methane_liquefaction_electro")  #Process turning methane gas into LBiquefied Methane - the condition methane needs to be turned into to be a sailable fuel
	Region = Region("region")        #Definition of the region where the plant is positioned
	Source = Source("renewable")  #sustainable e-fuels are sourced from wind and solar power
	Capacity = 1000   #The plant capacity
}


# bio-methanol -------------------------------------------------------
Plant "plant_methanol_bio_gasification" {
	Fuel = Fuel("methanol_bio")
	Process = Process("methanol_synthesis_bio_gasification")
	Region = Region("region")
	Source = Source("grid")
	
	Capacity = 1000
}

#  blue ammonia -------------------------------------------------------
Plant "plant_ammonia_blue" {
	Fuel = Fuel("ammonia_blue")
	Process = Process("haber_bosch_ccs_integrated_blue")
	Region = Region("region")
	Source = Source("grid")
	Capacity = 1000
}
```
:::

:::{dropdown} 0_includes_global/plot.inc
```python
# Definition of the plots produced for each scenario.
# Directory points at the "plots" subfolder of the scenario; each add_plot(...)
# selects one plot to produce.

Plot "plots" {
	Directory = "./plots/"

	add_plot("global_emission_absolute")
	add_plot("global_fuel_consumed")
	add_plot("plant_production_cost")
	add_plot("port_bunker_price")
}
```
:::

:::{dropdown} 0_includes_global/port.inc
```python
# Definition of port
Port "port" {
	set_bunker_price_overwrite("heavy_fuel_oil", 250)
	set_bunker_wtt_overwrite("heavy_fuel_oil", "carbon_dioxide", 0.62)
}
```
:::

:::{dropdown} 0_includes_global/process.inc
```python
# Definition of fuel processing

# Definition of "methane_liquefaction_electro"
Process "methane_liquefaction_electro" {  
	Feeds = [Process("methane_synthesis_electro")]
	Conversions = [1]
}

# Definition of "methane_synthesis_electro" 
Process "methane_synthesis_electro" {  
	Feeds = [Feedstock("demineralized_water"), Feedstock("carbon_dioxide_biogenic")]
	Conversions = [0.5, 2.75]  
}


# Definition of "methanol_synthesis_bio_gasification"
Process "methanol_synthesis_bio_gasification" {
	Feeds = [Feedstock("organic_wet_waste"), Feedstock("dry_wood_biomass")]
	Conversions = [1.21, 1.21]
}

# Definition of "haber_bosch_ccs_integrated_blue"
Process "haber_bosch_ccs_integrated_blue" {				
	Feeds = [Process("nitrogen_air_seperation"), Feedstock("natural_gas")]
	Conversions = [0.64, 0.822]						
}

# Definition of "nitrogen_air_seperation"
Process "nitrogen_air_seperation" {
}
```
:::

:::{dropdown} 0_includes_global/producer.inc
```python
# Definition of Producer

Producer "engineering_procurement_construction" {
	Plants = [Plant("plant_methane_electro"), Plant("plant_methanol_bio_gasification"), Plant("plant_ammonia_blue")]
	FuelDemandSensitivity = 1.5
	FuelCostSensitivity = 0.5

	MaximumDevelopment = 10
}
```
:::

:::{dropdown} 0_includes_global/producer_uptake.inc
```python
# Producer decision sensitivities are now set directly on the Producer in producer.inc
# (FuelDemandSensitivity, FuelCostSensitivity), so no separate uptake definitions are needed here.
```
:::

:::{dropdown} 0_includes_global/region.inc
```python
# Definition of region

Region "region" {
#set CapEx, OpEx, Process and feedstock WTT emissions for the different processes that produces the alternative fuels. The expensens and emissions related to the production of the fuels depend on the region.

### E-methane ###
	set_process_capex("methane_synthesis_electro", 100)
	set_process_opex("methane_liquefaction_electro", 88)
	set_process_energy("methane_synthesis_electro", 0.4)
	# liquefied e-methane
	set_process_capex("methane_liquefaction_electro", 200)
	set_process_energy("methane_liquefaction_electro", 0.6)
	# Set WTT feedstock emissions below:
	set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", -1)
	# Set WTT process emissions below:
	set_process_wtt("methane_liquefaction_electro", "carbon_dioxide", 0.5)

### Bio-methanol ###
	set_process_capex("methanol_synthesis_bio_gasification", 180)
	set_process_opex("methanol_synthesis_bio_gasification", 100)
	set_process_energy("methanol_synthesis_bio_gasification", 0.52)
	set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", -1.35)
	set_process_wtt("methanol_synthesis_bio_gasification", "methane", 0.00005)
	set_process_wtt("methanol_synthesis_bio_gasification", "nitrous_oxide", 0.00018)
	

### Blue ammonia ###
	set_process_capex("haber_bosch_ccs_integrated_blue", 200)
	set_process_opex("haber_bosch_ccs_integrated_blue", 50	) # combining ammonia plant opex and cost of CCS
	set_process_energy("haber_bosch_ccs_integrated_blue", 0.25)
	
	# Set WTT feedstock emissions below:
	set_feedstock_wtt("natural_gas", "carbon_dioxide", 0.11)
	set_feedstock_wtt("natural_gas", "methane", 0.0073)
	set_process_wtt("haber_bosch_ccs_integrated_blue", "carbon_dioxide", 0.180) #adding missing ccs of some carbon here
}
```
:::

:::{dropdown} 0_includes_global/report.inc
```python
# Export results to a subfolder called "plots".
# An error is raised if no such folder is found.

Report "report" {

	# Export results to a subfolder called "plots".
	# An error is raised if no such folder is found.
	Directory = "./plots/"
	
		
	# port
	add_port_property("*", BunkerIntensityPrice)				# USD/GJ
	add_port_property("*", BunkerIntensityTotalEquivalentWtt)	# kg / GJ
		
	# fleet
	add_fleet_property("*", TotalEquivalentWtt)		# ton/year
	add_fleet_property("*", TotalEquivalentTtw)		# ton/year
	add_fleet_property("*", TotalEquivalentWtw)		# ton/year
	add_fleet_property("*", TotalConsumedEnergy)	# GJ/year

	# global
	add_property(TotalEquivalentWtt)				# ton/year
	add_property(TotalEquivalentTtw)				# ton/year
	add_property(TotalEquivalentWtw)				# ton/year
	add_property(TotalConsumedEnergy)				# GJ/year
	add_property(ConsumedEnergy)					# GJ/year
	add_property(InstalledPower)					# MW
	
}
```
:::

:::{dropdown} 0_includes_global/route.inc
```python
# Definition of route 

Route "route" {
	RouteType = TRAMP
	Ports = [Port("port")]
	TimeAtSea = 0.75
	set_voyage_distribution("*", "*", 1)
	set_speed("*", "*", 10)
}
```
:::

:::{dropdown} 0_includes_global/source.inc
```python
# Definition of vessel finance

#Source of electricity for production of fuels
Source "renewable" {
	Dependency = CONNECTED
}

Source "grid" {  #blue and bio fuels sources electricity from the grid in the region where it is being produced.
	Dependency = CONNECTED
}
```
:::

:::{dropdown} 0_includes_global/tanks.inc
```python
# Definition of the pilot fuel tanks.  

Tank "pilot_oil" { 			
	FuelTypes = OIL
	Size = 2000 	
}

# Definition of main fuel tanks

Tank "main_oil" { 			
	FuelTypes = OIL
	Size = 9000 	
}

Tank "main_methane" { 			
	FuelTypes = METHANE 			
	Size = 9000 	
}

Tank "main_methanol" { 			
	FuelTypes = METHANOL 			
	Size = 9000 	
}

Tank "main_ammonia" { 			
	FuelTypes = AMMONIA 			
	Size = 9000 	
}
```
:::

:::{dropdown} 0_includes_global/time_steps_yearly.inc
```python
# This events file defines the timeline for the fleet transition module.

# Define the Start below.

Start

# A) TIME STEPS AND END OF TIMELINE
# Define annual time steps below.
Date "01-01-2025"
Date "01-01-2026"
Date "01-01-2027"
Date "01-01-2028"
Date "01-01-2029"
Date "01-01-2030"
Date "01-01-2031"
Date "01-01-2032"
Date "01-01-2033"
Date "01-01-2034"
Date "01-01-2035"
Date "01-01-2036"
Date "01-01-2037"
Date "01-01-2038"
Date "01-01-2039"
Date "01-01-2040"
Date "01-01-2041"
Date "01-01-2042"
Date "01-01-2043"
Date "01-01-2044"
Date "01-01-2045"
Date "01-01-2046"
Date "01-01-2047"
Date "01-01-2048"
Date "01-01-2049"
Date "01-01-2050"

# Define the End of the timeline.

End

### END OF time_steps_yearly.inc FILE
```
:::
