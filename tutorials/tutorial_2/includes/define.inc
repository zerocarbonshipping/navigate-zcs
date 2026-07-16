# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# This Tutorial 2 define.inc file is an edited copy of the define file from Tutorial 1. 
# Lengthy comments from tutorial 1 were removed to give you a better overview.

# The model definition and the Start of the timeline are the same as in tutorial 1.
ModelDefinition {
	StartDate = "01/01/2025"
}


# A) Definition of the fleets and nodes related to all vessels
# Ai) Container fleet
# Below is the definition of the fleet from tutorial 1. 
Fleet "fleet" {
	Vessels = [Vessel("vessel_ice_oil")]
	InterFuelSensitivity = 0.5
	IntraFuelSensitivity = 0.5
	InitialVessels = 100
}

# Aii) Bulk carrier fleet
# Paste the copy of the Fleet node "container_fleet" below, and make edits as
# described in the tutorial:


# Aiii) Decision sensitivities are now set directly on the fleet above
# (InterFuelSensitivity, IntraFuelSensitivity, TechnologySensitivity).


# B) DEFINITION OF ALL FOUR VESSELS
# Bi) Definition of fuel oil vessel
# Change the the value assigned to the attribute Tanks below.

Vessel "vessel_ice_oil" {
	PowerSystem = PowerSystem("ice_oil")
	Route = Route("route")
	NominalCapacity = 8000
	Tanks = [Tank("main_oil")]
	PropulsionLoad = 10
}

# Same as in tutorial 1.
PowerSystem "ice_oil" {
	Propulsion = Converter("propulsion_ice_oil")
	Electrical = Converter("electrical_ice_oil")
	Heat = Converter("heat_boiler_oil")
}

Converter "propulsion_ice_oil" {
	PowerCapacity = 50
	MainFuelTypes = OIL
	Efficiency = 0.5
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


# Bii) DEFINITION OF METHANE VESSEL
# This definition has the same structure as the definition of the fuel oil vessel, but has
# different assigned values.
#
# Define Vessel "container_ice_methane", Powersystem "ice_methane", Converter "propulsion_ice_methane", 
# Converter "electrical_ice_methane", Converter "heat_boiler_methane".
#
# Paste the nodes from section Bi) below.




# Biii) DEFINITION OF METHANOL VESSEL
#
# Define Vessel "bulk_ice_methanol", Powersystem "ice_methanol_bulk", Converter "propulsion_ice_methanol_bulk", 
# Converter "electrical_ice_methanol_bulk", Converter "heat_boiler_methanol_bulk".
#
# Paste the nodes from section Bi) below.




# Biv) DEFINITION OF AMMONIA VESSEL
#
# Define Vessel "bulk_ice_ammonia", Powersystem "ice_ammonia_bulk", Converter "propulsion_ice_ammonia_bulk", 
# Converter "electrical_ice_ammonia_bulk", Converter "heat_boiler_ammonia_bulk".
#
# Paste the nodes from section Bi) below.



# C) GENERAL SPECIFICATIONS FOR VESSELS

# Define the vessel route below (same as in tutorial 1). 
Route "route" {
	RouteType = REGIONAL_TRIP
	Ports = [Port("port")]
	TimeAtSea = 0.75
	ConditionDistribution = [1.0]
	Speeds = [10]
}


# Define the vessel tank below.
Tank "main_oil" {
	FuelTypes = OIL
	Size = 9000
}

# Ci) DEFINITION OF PILOT TANK
# Define Tank "pilot_oil".
# Paste the node Tank "main_oil" from section C) below.


# Cii) DEFINITION OF METHANE TANK
# Define Tank "main_methane".
# Paste the node Tank "main_oil" from section C) below.



# Ciii) DEFINITION OF METHANOL TANK
# Define Tank "main_methanol".
# Paste the node Tank "main_oil" from section C) below.



# Civ) DEFINITION OF AMMONIA TANK
# Define Tank "main_ammonia".
# Paste the node Tank "main_oil" from section C) below.



# D) DEFINITION OF THE PORT AND THE REGION
# Definition of the node "port" and BunkeringLogistics from tutorial 1 below:
Port "port" {
	set_bunker_price_overwrite("heavy_fuel_oil", 250)
	set_bunker_wtt_overwrite("heavy_fuel_oil", "carbon_dioxide", 0.62)
}


BunkerLogistics {
	LiquidMarketFuels = [Fuel("heavy_fuel_oil")]
}


# Definition of the node "Region" 

	# e-methane
	

	# Bio-methanol
	

	# Blue ammonia
	


# E) DEFINITION OF ALL FOUR FUELS
# Ei) Definition of heavy_fuel_oil

# Definition of "heavy_fuel_oil" (same as Tutorial 1).
Fuel "heavy_fuel_oil" {
	FuelType = OIL
	LowerHeatingValue = 41.2
	MassDensity = 0.9

	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}

Emission "carbon_dioxide" {
	GlobalWarmingPotential = 1
}

Emission "methane" {
	GlobalWarmingPotential = 25
}

Emission "nitrous_oxide" {
	GlobalWarmingPotential = 273
}


# Eii) Definition of electro-methane
# Define the methane production plant Plant "plant_methane_electro"


# define fuel and processes
# Define Fuel "methane_electro"


# Define Process "methane_liquefaction_electro"



# Define Process "methane_synthesis_electro"



# Define Feedstocks



# Eiii) Definition of bio-methanol
# Paste the nodes "plant_methane_electro", Fuel "methane_electro", "methane_synthesis_electro", Feedstock "demineralized_water" and Feedstock "carbon_dioxide_biogenic"  from section Bi) below:



# Eiv) Definition of blue ammonia
# Paste the nodes "plant_methane_electro", Fuel "methane_electro", "methane_synthesis_electro", Feedstock "demineralized_water" and Feedstock "carbon_dioxide_biogenic"  from section Bii) below:


# Ev) Definition of electricity source
# Paste the Source nodes "renewable" and Source "grid"

# F) Definition of Fuel Producer node
# Define the Producer "engineering_procyurement_construction_global"


# Set the producer decision sensitivities (FuelDemandSensitivity, FuelCostSensitivity)



# G) DEFINITION OF OUTPUT (PLOTS)
# Define a Plot node "plots" below. Use the Directory attribute to point at the
# "plots" subfolder, and add_plot(...) for each plot you want produced (see the
# tutorial for the plot labels to include).



# END OF NAV FILE