<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Tutorial 2

**Why are you doing this tutorial?**

In Tutorial 1, you learned about the foundations of how to run a model with the most necessary parameters in Navigate. However, the basic scenario of only one vessel and only one fuel is not very useful for predicting the future of shipping and simplifies what Navigate can do. In this tutorial, you will simulate a slightly more complex scenario, with two different vessel segments, four different fuels, manipulations of trade growth, etc. At the end of this tutorial, you will have learned how to set up a more complex environment with more variables. You will also be able to interpret more complex projections and put them in context. 

**Setting the scene:**

In this scenario, we look at a case where we have 2 fleets. One fleet consists of 2 container ships, and the other fleet consists of 2 bulk carriers. One of the container ships is a mono-fuel fuel oil vessel, the other one is a dual-fuel methane. One of the bulk carriers is a dual-fuel methanol, the other one a dual-fuel ammonia.
Note: The specifications of alternative fuel vessels, for example, the power capacity, are not edited/changed from tutorial 1 to tutorial 2, to keep this tutorial simple. But note that these specifications do not reflect Navigate’s default specifications in any way. Therefore, the results you get are not very realistic and will differ significantly from a simulation done in Navigate with Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping’s assumptions. You can find the defaults used for different attributes in Navigate under `Navigate/navigate/defaults/installation/*`. 

**How does it work?**

In the folder `tutorial_2`, we have prepared a `define.inc`, an `events.inc` and a `tutorial_2.nav` file for you. The files will include prompts that tell you what to do, just like in Tutorial 1. All of the files for Tutorial 2 build on what you have already created in Tutorial 1. This means, that all nodes from the files from Tutorial 1 are already included in the files you will be working with for Tutorial 2. Edits made to accommodate the new vessel and fuel assumptions in this tutorial are specified in this guide.
In the last section, you will produce plots and manipulate some variables. You will explore the projections on the global emissions, global fuel cost etc., for the two different fleets, taking into account emissions that are associated with the sourcing and production of the fuels, as well as the emissions from burning the fuel. We will also explore the effect of trade growth over time.


## Modifying the `define.inc` file

Open the `includes` folder in the `tutorial_2`-folder and open the `define.inc` file.
Leave Model Definition and the Start of the timeline as they are from tutorial 1.

### Setting up the Fleets

#### Container Fleet
You will adopt the definition of the one fleet that we created in tutorial 1 and make some edits.

1. Change the name of the `Fleet` node from `"fleet"` to `"container_fleet"`.
2. Rename `Vessel("vessel_ice_oil")` to `Vessel("container_ice_oil")`.
Add the `Vessel("container_ice_methane")` to the list assigned to the attribute Vessels.
3. Set the `TradeGrowth` in the container fleet to 5% increase annually.

```python
Fleet "container_fleet" {	
   Vessels = [Vessel("container_ice_oil"), Vessel("container_ice_methane")] 
   InterFuelSensitivity = 0.5
   IntraFuelSensitivity = 0.5
   InitialVessels = 100 
   TradeGrowth = 0.05
}
```

4. Copy the entire node `"container_fleet"` and paste it into section *Bulk Fleet*).

#### Bulk Fleet

You will adopt the definition of the one fleet that we created in tutorial 1 and make some edits.

1. Change the name of the fleet node from `"container_fleet"` to `"bulk_fleet"`.
2. Change the assigned value to Vessels to a list including `[Vessel("bulk_ice_methanol"), Vessel("bulk_ice_ammonia")]`.
3. We assume that the number of initial vessels in the container and the bulk fleet are identical, just like the trade growth.

```python
Fleet "bulk_fleet" {	
   Vessels = [Vessel("bulk_ice_methanol"), Vessel("bulk_ice_ammonia")] 
   InterFuelSensitivity = 0.5
   IntraFuelSensitivity = 0.5
   InitialVessels = 100
   TradeGrowth = 0.05
}
```

4. As in tutorial 1, the decision sensitivities are set directly on each fleet through the `InterFuelSensitivity` and `IntraFuelSensitivity` attributes above (a value of `0.5` means a 10% higher LCOT halves the odds) — there is no separate node to define.

### Definition of all four Vessels

#### Fuel Oil Vessel

The fuel oil vessel `"vessel_ice_oil"` you defined in Tutorial 1 corresponds to the fuel oil vessel `"container_ice_oil"` in this Tutorial 2. Hence, we only need to make a few edits to the instructions. The edits are necessary because you will add new fuels to the simulation, so you need to be more specific about what type of tank, engine etc., it is. 

1. Change the name of the node from `"vessel_ice_oil"` to `"container_ice_oil"`.
This tutorial has two different types of vessels, so they are named accordingly, in order to differentiate them.

```python
Vessel "container_ice_oil" {
   PowerSystem = PowerSystem("ice_oil")
   Route = Route("route")		
   NominalCapacity = 8000
   Tanks = [Tank("main_oil")]						
   PropulsionLoad = 10				
}
```

2. Copy the section above — but only the four nodes Vessel `"container_ice_oil"`, PowerSystem `"ice_oil"`, Converter `"propulsion_ice_oil"`, and Converter `"electrical_ice_oil"` — and paste it three times into Bii), Biii) and Biv).

   Do **not** copy `Converter "heat_boiler_oil"`. There is a single shared heat boiler that every vessel reuses through `Heat = Converter("heat_boiler_oil")`, so it is defined once in Bi) only. Copying it as well would create duplicate node definitions and the model would fail to parse.


#### Methane Vessel

You just copied all the nodes from the fuel oil vessel’s definition into this section. In the following steps, you will edit the instructions, so it becomes the definition of a second vessel, namely a methane vessel. 

1. Define Vessel `"container_ice_methane"`: 
   1. Change the name of the copied node from
    `"container_ice_oil"` to `"container_ice_methane"`.
   2. Change the assigned value for `PowerSystem` to `PowerSystem("ice_methane")`.
   3. Change the assigned value for `Tanks` to `[Tank("main_methane"), Tank("pilot_oil")]`. 
   Next to the main tank for methane, you also need to include the pilot tank for fuel oil here, as a methane vessel requires fuel oil too. You will define both tanks later on).

```python
Vessel "container_ice_methane" {
   PowerSystem = PowerSystem("ice_methane")
   Route = Route("route")		
   NominalCapacity = 8000
   Tanks = [Tank("main_methane"), Tank("pilot_oil")]	
   PropulsionLoad = 10				
}
```

2. Define PowerSystem `"ice_methane"`: 
   1. Change the name of the node to `"ice_methane"`.
   2. Change the assigned value for Propulsion to `Converter("propulsion_ice_methane")`.
   3. Change the assigned value for Electrical to `Converter("electrical_ice_methane")`.

```python
PowerSystem "ice_methane" {
   Propulsion = Converter("propulsion_ice_methane")
   Electrical = Converter("electrical_ice_methane")
   Heat = Converter("heat_boiler_oil")
}
```

3. Define Converter `"propulsion_ice_methane"`:
   1. Change the name of the node to Converter `"propulsion_ice_methane"`. The propulsion engine is the main engine for an internal combustion engine (ice).
   2. Change the assigned value for `MainFuelTypes` to `METHANE`. `MainFuelTypes` describe the main fuel types that a specific engine can run on.
   3. Set the `PilotFuelTypes` to be `OIL`, and the `MinimumPilotFuel` to 5%. 
   4. Set the slip TTW emissions for methane to 0.01. The unit describes the emissions associated with the tons of slipped fuel per tons of fuel, i.e., a percentage. In this case, 1% of the fuel methane in the converter is not combusted but "slips", due to imperfect combustion processes. So the emissions from one ton of methane fuel escape into the atmosphere because a fraction of the methane is not combusted.

```python
Converter "propulsion_ice_methane" { 
   PowerCapacity = 50  
   MainFuelTypes = METHANE
   PilotFuelTypes = OIL
   MinimumPilotFuel = 0.05
   Efficiency = 0.51
   set_slip_fraction(METHANE, 0.01)
}
```

4. Define Converter `"electrical_ice_methane"`:
   1. Change the name of the node to `"electrical_ice_methane"`. The electrical engine is the auxiliary engine for an internal combustion engine (ice).
   2. Change the assigned value for `MainFuelTypes` to `METHANE`.
   3. Add the `PilotFuelTypes` to be `OIL`, and set the `MinimumPilotFuel` to 5%.
   4. Set the slip TTW emissions for methane to 0.01.

```python
Converter "electrical_ice_methane" { 
   PowerCapacity = 10 
   MainFuelTypes = METHANE
   PilotFuelTypes = OIL
   MinimumPilotFuel = 0.05
   Efficiency = 0.5
   set_slip_fraction(METHANE, 0.01)
}
```

#### Methanol Vessel

You previously copied all the nodes from the fuel oil vessel’s definition into this section. 
You now edit it by essentially repeating the same steps from the section above, i.e. from the definition of the methane vessel. 

1. Define `Vessel` `"bulk_ice_methanol"`:
   1. Change the name from `"container_ice_oil"` to `"bulk_ice_methanol"`.
   2. Change the assigned value for `PowerSystem` to `PowerSystem("ice_methanol")`.
   3. Change the assigned value for Tanks to `[Tank("main_methanol"), Tank("pilot_oil")]`.
Next to the main tank for methanol, you also need to include the pilot tank for fuel oil here, as a methanol vessel requires fuel oil to operate. 


```python
Vessel "bulk_ice_methanol" {
   PowerSystem = PowerSystem("ice_methanol")
   Route = Route("route")		
   NominalCapacity = 8000
   Tanks = [Tank("main_methanol"), Tank("pilot_oil")]	
   PropulsionLoad = 10				
}
```

2. Define `PowerSystem` `"ice_methanol_bulk"`:
   1. Change the name of the node to `PowerSystem` `"ice_methanol"`.
   2. Change the assigned value for Propulsion to `Converter("propulsion_ice_methanol")`.
   3. Change the assigned value for Electrical to `Converter("electrical_ice_methanol")`.

```python
PowerSystem "ice_methanol" {
   Propulsion = Converter("propulsion_ice_methanol")
   Electrical = Converter("electrical_ice_methanol")
   Heat = Converter("heat_boiler_oil")
}
```

3. Define the `Converter` `"propulsion_ice_methanol"`:
   1. Change the name of the node to `"propulsion_ice_methanol"`.
   2. Change the assigned value for `MainFuelTypes` to `METHANOL`.
   3. Set the `PilotFuelTypes` to be `OIL`, and the `MinimumPilotFuel` to 5%. This describes what fuel type is acting as a pilot fuel, and how much is needed.

```python
Converter "propulsion_ice_methanol" {
   PowerCapacity = 50
   MainFuelTypes = METHANOL
   PilotFuelTypes = OIL
   MinimumPilotFuel = 0.05
   Efficiency = 0.51
}
```

4. Define `Converter` `"electrical_ice_methanol"`:
   1. Change the name of the node to `Converter` `"electrical_ice_methanol"`.
   2. Change the assigned value for `MainFuelTypes` to `METHANOL`.
   3. Set the `PilotFuelTypes` to be `OIL`, and the `MinimumPilotFuel` of 5%. 

```python
Converter "electrical_ice_methanol" { 
   PowerCapacity = 10 
   MainFuelTypes = METHANOL
   PilotFuelTypes = OIL
   MinimumPilotFuel = 0.05
   Efficiency = 0.5
}
```

#### Ammonia Vessel

You previously copied all the nodes from the fuel oil vessel’s definition into this section. 
You now edit it by essentially repeating the same steps from the previous section), i.e. from the definition of the methanol vessel.


1. Define `Vessel` `"bulk_ice_ammonia"`:
   1. Change the name from `"container_ice_oil"` to `"bulk_ice_ammonia"`.
   2. Change the assigned value for `PowerSystem` to `PowerSystem("ice_ammonia")`.
   3. Change the assigned value for Tanks to `[Tank("main_ammonia"), Tank("pilot_oil")]`.
Next to the main tank for ammonia, you also need to include the pilot tank for fuel oil here, as an ammonia vessel requires fuel oil to operate. 
You will define both tanks later.

```python
Vessel "bulk_ice_ammonia" {
   PowerSystem = PowerSystem("ice_ammonia")
   Route = Route("route")		
   NominalCapacity = 8000
   Tanks = [Tank("main_ammonia"), Tank("pilot_oil")]	
   PropulsionLoad = 10				
}
```

2. Define `PowerSystem` `"ice_ammonia_bulk"`:
   1. Change the name of the node to PowerSystem `"ice_ammonia"`.
   2. Change the assigned value for Propulsion to `Converter("propulsion_ice_ammonia")`.
   3. Change the assigned value for Electrical to `Converter("electrical_ice_ammonia")`.

```python
PowerSystem "ice_ammonia" {
   Propulsion = Converter("propulsion_ice_ammonia")
   Electrical = Converter("electrical_ice_ammonia")
   Heat = Converter("heat_boiler_oil")
}
```

3. Define Converter `"propulsion_ice_ammonia"`:
   1. Change the name of the node to Converter `"propulsion_ice_ammonia"`.
   2. Change the assigned value for `MainFuelTypes` to `AMMONIA`.
   3. Set the `PilotFuelTypes` to be `OIL`, and the `MinimumPilotFuel` to 5%. 

```python
Converter "propulsion_ice_ammonia" {
   PowerCapacity = 50
   MainFuelTypes = AMMONIA
   PilotFuelTypes = OIL
   MinimumPilotFuel = 0.05
   Efficiency = 0.51
}
```

4. Define Converter `"electrical_ice_ammonia"`:
   1. Change the name of the node to Converter `"electrical_ice_ammonia"`.
   2. Change the assigned value for `MainFuelTypes` to `AMMONIA`.
   3. Set the `PilotFuelTypes` to `OIL`, and the `MinimumPilotFuel` to 5%.

```python
Converter "electrical_ice_ammonia" {
   PowerCapacity = 10
   MainFuelTypes = AMMONIA
   PilotFuelTypes = OIL
   MinimumPilotFuel = 0.05
   Efficiency = 0.5
}
```

### General Specifications for Vessels

You will set:

- Definitions of nodes related to all vessels
- The node related to the vessel route is the same as in tutorial 1.
- The vessel tank node has also been moved to the beginning of the file but needs to be edited.

1. Copy the node `"main_oil"` and paste one copy into sections Ci), Cii), Ciii), Civ), respectively.

#### Pilot Tank

2. For the first pasted node `"main_oil"` in section Ci), change the name of the node from `"main_oil"` to `"pilot_oil"`.
3. Change the Size to 2000.

```python
Tank "pilot_oil" {
   FuelTypes = OIL
   Size = 2000
}
```

#### Methane Tank

The methane vessel will have a pilot fuel tank for fuel oil, and a main tank for green methane. 

4. Define the main tank with the instructions block below. Note that it has a different fuel type.

```python
Tank "main_methane" {
   FuelTypes = METHANE
   Size = 9000
}
```

#### Methanol Tank

The methanol vessel will have a pilot fuel tank for fuel oil, and a main tank for methanol. 

5. Define the main tank with the instructions block below. 
Note that it has a different fuel type.

```python
Tank "main_methanol" {
   FuelTypes = METHANOL
   Size = 9000
}
```

#### Ammonia Tank

The ammonia vessel will have a pilot fuel tank for fuel oil, and a main tank for ammonia. 

6. Define the main tank with the instructions block on the right. 
Note that it has a different fuel type.

```python
Tank "main_ammonia" {
	FuelTypes = AMMONIA
	Size = 9000
}
```

### Definition of the Port and the Region

You take over the definition of the port from the tutorial 1 but will edit it.

The price and emissions of fuels can be modelled in two ways. The first is as in tutorial 1 where the price and WTT emissions are assigned on a specific port. The second is a bottom-up approach defining the feedstock to fuel process flow, plants, producers building plants, and assigning the cost of feedstock and individual process components on a regional level using the Region node.

In this tutorial you will continue to define heavy fuel oil on the port level but the other fuels will be modelled bottom-up.


#### Port

The `Port` `"port"` and `BunkerLogistics` nodes are carried over from tutorial 1. Update the heavy fuel oil bunker price from 250 to 120; the WTT emission factor and `BunkerLogistics` stay the same.

```python
Port "port" {
   set_bunker_price_overwrite("heavy_fuel_oil", 120)
   set_bunker_wtt_overwrite("heavy_fuel_oil", "carbon_dioxide", 0.62)			
}

BunkerLogistics {
   LiquidMarketFuels = [Fuel("heavy_fuel_oil")]
}
```

#### Region

In this example the two fleets solely operate within the same single region. The emissions associated with producing the fuels and the cost of these fuels are dependent on the region where the fleets are fueled.

1. Define the region node on which the feedstock and process costs and emissions will be defined.

```python
Region "region" {
}
```

##### Electro-Methane

*Costs and emissions associated with producing, electro-methane from point source will be defined.*

Producing electro methane with carbon dioxide from point source requires a two-step procedure.
First is methane synthesis from a point source, such as a biogas facility. The process has an associated CapEx and OpEx cost, along with an energy demand.
The feedstock required by this process is biogenic carbon dioxide. The biogenic carbon is sourced from waste such as manure, agricultural waste, food waste. So, it is carbon that would be emitted 'naturally', but instead it can be captured and processed to become an alternative fuel.
This causes a negative WTT emission of carbon dioxide as the gas is captured for methane production instead of released.
When the fuel is combusted, the captured and processed carbon is eventually emitted. Because the carbon would have been emitted anyway if it had not been captured and not made it into an alternative fuel, the well-to-tank emission factor for the feedstock is -1 (i.e., -100%), in order to balance the TTW emissions in Navigate, so the final net emissions are zero.

To the CO2, compressed hydrogen is added, which is produced using electricity, with a feedstock of demineralized water. In this tutorial it is assumed that no emissions are associated with this feedstock. 
The synthesized methane is an intermediate fuel that is not a bunker fuel, i.e., cannot be used for the propulsion of a ship. 
That is why you do not specify a feedstock cost, but the OPEX costs related to the process `"methane_liquefaction_electro"`.

The Liquefaction process also have an associated CapEx and energy demand. 
The process of liquefying the methane into a bunkering fuel result in carbon dioxide emissions. 

1. Within the curly brackets of `Region` `"region"` set the cost and well-to-tank emissions associated with the production of electro-methane.

```python
   set_process_capex("methane_synthesis_electro", 100)
   set_process_energy("methane_synthesis_electro", 0.4)
   set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", -1)
   
   set_process_capex("methane_liquefaction_electro", 200)
   set_process_opex("methane_liquefaction_electro", 88)
   set_process_energy("methane_liquefaction_electro", 0.6)
   set_process_wtt("methane_liquefaction_electro", "carbon_dioxide", 0.5)
```

##### Bio-Methanol

Bio-methanol is made by synthesizing methane emissions from biogenic carbon. 
Here you add the CapEx, OpEx and energy demand of the methanol synthesis. 
Bio-methanol has biogenic feedstock as carbon, and from a WTT scope, the use of biogenic carbon dioxide in methanol production results in unavoided emissions of carbon dioxide.
Negative emissions per se don’t exist, but in Navigate, we use this negative factor as a means to balance out the positive TTW emissions of bio-methanol. Hence, the overall WTW emissions from bio-methanol will be 0 in the model, because the feedstock (i.e. the ‘ingredient’) for bio-methanol would have led to emissions anyway if it would not have been transformed into fuel.

2. Within the curly brackets of `Region` `"region"` set the cost and well-to-tank emissions associated with the production of bio-methanol.

```python
   set_process_capex("methanol_synthesis_bio_gasification", 180)
   set_process_opex("methanol_synthesis_bio_gasification", 100)
   set_process_energy("methanol_synthesis_bio_gasification", 0.52)
   
   set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", -1.35)
   set_process_wtt("methanol_synthesis_bio_gasification", "methane", 0.00005)
   set_process_wtt("methanol_synthesis_bio_gasification", "nitrous_oxide", 0.00018)
```

##### Blue Ammonia

For blue ammonia, the CapEx and OpEx of the ammonia plant and the carbon capture and storage (CCS) have been combined and are represented in the integrated Harber Bosch process.
The same for energy demand.

3. Set the well-to-tank `"carbon_dioxide"` and `"methane"` emissions associated with the feedstock `"natural_gas"`, for both CO2 and methane.
4. Set the well-to-tank `"carbon_dioxide"` emissions associated with the process `"haber_bosch_ccs_integrated_blue"`.  

```python
   set_process_capex("haber_bosch_ccs_integrated_blue", 200)
   set_process_opex("haber_bosch_ccs_integrated_blue", 50) 
   set_process_energy("haber_bosch_ccs_integrated_blue", 0.25)
   
   set_feedstock_wtt("natural_gas", "carbon_dioxide", 0.11)
   set_feedstock_wtt("natural_gas", "methane", 0.0073)
   
   set_process_wtt("haber_bosch_ccs_integrated_blue", "carbon_dioxide", 0.180)
```

### Definition of Fuels

You can leave the definition of heavy fuel oil as it is from tutorial 1. For alternative fuels, a definition of a `"plant"` is needed.

#### Electro Methane Plant

The `"plant"` node represents a fuel production plant that produces fuel. It is assumed that the entire production process occurs within the plant.

1. Define Plant `"plant_methane_electro"`. The node Plant `"plant_methane_electro"`
Contains the inputs and outputs of e-methane production from point source carbon capture.
2. Set Fuel type to `Fuel("methane_electro")`
This fuel type is e-methane with biogenic carbon from a points source.
3. Set the value assigned to `Process` to `Process("methane_liquefaction_electro")`.
This is the final process in the process tree which produces the bunker fuel liquefied e-methane.
4. Set the value assigned to `Region` to `Region("region")`.
This determines the region where the plant is located, which has an effect on the cost and WTT emissions of the fuel.
5. Set the energy source to `"renewable"`. 
e-fuels need to be sourced from renewable energy sources. 
6. Set plant capacity to 1000.
7. Set plant construction lead time to 4 years.

```python
Plant "plant_methane_electro" {
   Fuel = Fuel("methane_electro")   
   Process = Process("methane_liquefaction_electro")  
   Region = Region("region")   
   Source = Source("renewable")  
   Capacity = 1000
   LeadTime = 4
}
```

8. Define the Fuel node `"methane_electro"`. This is the e-methane fuel the plant produces; the `Plant` above references it through `Fuel("methane_electro")`, so it must exist.
   1. Add a node of the type Fuel and name it `"methane_electro"`.
   2. Set `FuelType` to `METHANE`.
   3. Set `LowerHeatingValue` to 50 and `MassDensity` to 0.43.
   4. Set the TTW emission factor for `"carbon_dioxide"` to 2.75.

```python
Fuel "methane_electro" {
   FuelType = METHANE
   LowerHeatingValue = 50
   MassDensity = 0.43
   set_ttw("carbon_dioxide", 2.75)
}
```

9. Define the process node `"methane_liquefaction_electro"`.

It has one assigned feedstock which need to be defined later.
Set the conversion factors for the feedstocks. A conversion factor describes the tons of 'feedstock' required to produce one ton of fuel.
Notice that the feedstock to the liquefaction process is the output of another process.

```python
Process "methane_liquefaction_electro" {
   Feeds = [Process("methane_synthesis_electro")]
   Conversions = [1]
}
```

10. Define process `"methane_synthesis_electro"`:
   1. Add a node of the type Process and name it `"methane_synthesis_electro"`.
   2. Add two types of feedstocks to this process, and name them: `"demineralized_water"` and `"carbon_dioxide_biogenic"`.
   The demineralized water is used to produce e-hydrogen, and the rest of the molecule comes from point source carbon capture of biogenic carbon.
   3. Set the conversion rates. This means that the process sources 0,5 tons of hydrogen (requiring 4.5 tons of demineralized water) and 2,75 tons of CO2 per ton of fuel.

```python
Process "methane_synthesis_electro" {
   Feeds = [Feedstock("demineralized_water"), Feedstock("carbon_dioxide_biogenic")]
   Conversions = [4.5, 2.75]
}
```

11. Define feedstock `"demineralized_water"` and define feedstock `"carbon_dioxide_biogenic"`:
    1. Add a node of the type feedstock and name it `"demineralized_water"`.
    2. Add a node of the type feedstock and name it `"carbon_dioxide_biogenic"`.

```python
Feedstock "demineralized_water" {
}
Feedstock "carbon_dioxide_biogenic" {
}
```

#### Bio-Methanol Plant

1. Copy  with the nodes Plant `"plant_methane_electro"`, Fuel `"methane_electro"`.,Process `"methane_synthesis_electro"`. Paste into Eiii) and Eiiii).
2. Define Plant `"plant_methanol_bio_gasification"`:
   1. Change the plant name to `"plant_methanol_bio_gasification"`.
   2. Change the fuel to `"methanol_bio"`.
   3. Change the process to `"methanol_synthesis_bio_gasification"`. 
   4. Change the electricity source to `"grid"`.
   The electricity used to power the plant is from the region's electricity grid.
   5. The Region, Capacity, and LeadTime of the plant is the same as for methane, for the sake of simplicity.

```python
Plant "plant_methanol_bio_gasification" {     
   Fuel = Fuel("methanol_bio")   
   Process = Process("methanol_synthesis_bio_gasification")  
   Region = Region("region")  
   Source = Source("grid")  
   Capacity = 1000
   LeadTime = 4
}
```

3. Define `"methanol_bio"`:
   1. Change the name of the node to "methanol_bio". 
   2. Change the value assigned to FuelType to METHANOL. 
   3. Change the value assigned to LowerHeatingValue to 19.9. 
   4. Change the value assigned to MassDensity to 0.791. 
   5. Change the TTW emission factor for "carbon_dioxide" to 1.38 tons of emissions/liter of fuel. 
   6. Delete the lines that add the TTW emission factors for methane and nitrous oxide, because we do not consider methane or nitrous oxide emissions from bio-methanol, or it is not applicable.

```python
Fuel "methanol_bio" {
   FuelType = METHANOL
   LowerHeatingValue = 19.9 
   MassDensity = 0.791
   set_ttw("carbon_dioxide", 1.38)
}
```

4. Define `"methanol_synthesis_bio_gasification"`:
   1. Change the name of the process node to `"methanol_synthesis_bio_gasification"`. 
   2. Change the value assigned to Feedstocks to `[Feedstock("organic_wet_waste"), Feedstock("dry_wood_biomass")]`. You need to include two feedstocks in the list, as bio-methanol requires both for the production. 
   3. Change the value assigned to Conversions to `[1.21, 1.21]`.

```python
Process "methanol_synthesis_bio_gasification" {
   Feeds = [Feedstock("organic_wet_waste"), Feedstock("dry_wood_biomass")]
   Conversions = [1.21, 1.21]		
}
```

5. Define `"organic_wet_waste"` and define `"dry_wood_biomass"`:
   1. Add a node of type feedstock and name it "organic_wet_waste".
   2. Add a node of the type feedstock and name it "dry_wood_biomass".

```python
Feedstock "organic_wet_waste" {
}

Feedstock "dry_wood_biomass" {
}
```

#### Blue Ammonia Plant

1. Define `"plant_ammonia_blue"`:
   1. Change the plant name to `"plant_ammonia_blue"`. 
   2. Change the fuel to `"ammonia_blue"`. 
   3. Change the process to `"haber_bosch_ccs_integrated_blue"`. 
   4. Change the electricity source to `"grid"`. The electricity used to power the plant and the Haber Bosch process is from the region's electricity grid. 
   6. The Region, Capacity, and LeadTime of the plant is the same as for methane, for the sake of simplicity.

```python
Plant "plant_ammonia_blue" {
   Fuel = Fuel("ammonia_blue")   
   Process = Process("haber_bosch_ccs_integrated_blue")  
   Region = Region("region")  
   Source = Source("grid")  
   Capacity = 1000
   LeadTime = 4
}
```

2. Define `"ammonia_blue"`:
   1. Change the name of the node to `"ammonia_blue"`. 
   2. Change the value assigned to `FuelType` to `AMMONIA`. 
   3. Change the value assigned to `LowerHeatingValue` to 18.8. 
   4. Change the value assigned to `MassDensity` to 0.623. 
   5. Delete all lines that add emission factors. This is because combustion of ammonia does not produce CO2 emissions as no carbon is contained in the fuel.

```python
Fuel "ammonia_blue" {
   FuelType = AMMONIA
   LowerHeatingValue = 18.8 
   MassDensity = 0.623
}
```

3. Define `"haber_bosch_ccs_integrated_blue"`:
   1. Change the name of the process node to `"haber_bosch_ccs_integrated_blue"`.
The harber-bosch process produces ammonia, and here it is integrated with CCS, resulting in abated fossil emissions from the natural gas used as feedstock. 
   2. Change the value assigned to Feedstocks to `[Process("nitrogen_air_seperation"), Feedstock("natural_gas")]`.
You need to include two feedstocks in the list, as blue ammonia requires both for the production. 
These are nitrogen from air separation, which is the output of a process, and the feedstock of Natural gas. 
   3. Change the value assigned to Conversions to `[0.64, 0.822]`. 
   4. Change the name of the feedstock node to `"natural_gas"`.


```python
Process "haber_bosch_ccs_integrated_blue" {
   Feeds = [Process("nitrogen_air_seperation"), Feedstock("natural_gas")]
   Conversions = [0.64, 0.822]
}
```

4. Define `"natural_gas"` and define `"nitrogen"`
   1. Define the feedstock node `"natural_gas"`.
In reality, nitrogen is an intermediate fuel and would be defined as a `Fuel` in Navigate. For simplicity in this tutorial though, we have defined it as a `Feedstock`.
   2. Define the Process node `"nitrogen_air_seperation"`.
For the sake of simplicity, this node is empty, but in Navigate you will be able to find that a range of processes contribute to the production of blue ammonia. From the process of nitrogen air separation nitrogen is captured, along with other air particle. If this process is combined with CCS the fossil emissions from the natural gas the blue ammonia are abated.

```python
Feedstock "natural_gas" {	
}

Process "nitrogen_air_seperation" {
}
```

#### Definition of an Electricity Source

The production plants have the attribute ‘Source’, which represent the source of electricity used in the process. This node must be created to integrate as an attribute within the fuel production node.

1. Define the node Source `"renewable"`. Give it the value of `Dependency = CONNECTED`. 
2. Define the node Source `"grid"`. Give it the value of `Dependency = CONNECTED`.



### Definition of a Producer Node

The producer node is similar to the fleet node but for plants instead of vessels. It is used to model which fuel plants are built and thus which types and how much fuel is available to be used by the vessels.

1. Define the node Producer `"engineering_procurement_construction_global"`
2. Define the 3 plants that the producer may choose between when deciding what fuel supply to scale up. 
3. Set the `MaximumDevelopment` to 10, which is the constraint on how many plants can be built per year.

```python
Producer "engineering_procurement_construction_global" {
   Plants = [Plant("plant_methane_electro"),
             Plant("plant_methanol_bio_gasification"),
             Plant("plant_ammonia_blue")]
   MaximumDevelopment = 10
   FuelDemandSensitivity = 1.5
   FuelCostSensitivity = 0.5
}
```

4. `FuelDemandSensitivity` controls how strongly the choice *between fuel pathways* responds to expected demand: a value of `1.5` means a pathway whose expected demand is 10% higher receives 1.5x the odds (higher demand is better, so use a value above `1`). This lets the EPC scale up the fuel with the largest gap between demand and production capacity.
5. `FuelCostSensitivity` controls the choice *between plants producing the same fuel* by their levelized cost of fuel (LCoF): a value of `0.5` means a plant whose LCoF is 10% higher receives half the odds (lower cost is better, so use a value below `1`).

### Definition of a `Plot` Node

The `Plot` node defines which output plots Navigate produces and where they are saved. Navigate only generates plots when at least one `Plot` node is defined.

1. Define a node `"plots"` with the node type `Plot`.
2. Set the `Directory` attribute to `"./plots/"`. This is the subfolder, relative to the `.nav` file, where the plots are saved. Navigate creates the folder if it does not already exist.
3. Use the `add_plot(...)` command once per plot you want produced. In this tutorial we now also have fuel production, so in addition to the absolute emissions, the global fuel mix, and the bunker price at the port, we also produce the plant production cost.

```python
Plot "plots" {
    Directory = "./plots/"

    add_plot("global_emission_absolute")
    add_plot("global_fuel_consumed")
    add_plot("plant_production_cost")
    add_plot("port_bunker_price")
}
```

## The `EVENTS` input file

1. Open the ‘includes’ folder in the `tutorial_2`-folder and open the ‘events.inc’ file.
2. Define `Start`. You will define the `End` later.
3. Because we want Navigate to run simulations until 2050, you need to define intermediate time steps until 2050. In Navigate we have decided on annual time steps, but one could also decide on 5-year time steps, for example. **Define annual time steps with a reference Date.**
4. Mark the end of the timeline with `End`.

```python
Start
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
End
```

## Running analyses and interpreting results

1. Use the terminal to navigate to the `tutorial_2` folder. Recall `cd path/to/folder` and `cd ..`
2. Run the command `navigate tutorial_2.nav`
3. Look through the plots folder and interpret the results.