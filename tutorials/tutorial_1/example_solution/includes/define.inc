# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# This is an example of a DEFINE file with the minimum amount 
# of parameters needed to run a meaningful modelling scenario in Navigate. 

# Define ModelDefinition below.
ModelDefinition {
	StartDate = "01/01/2025"
}


# A) DEFINITION OF A FLEET
# Define the node "fleet" below.
Fleet "fleet" {
	Vessels = [Vessel("vessel_ice_oil")]
	InterFuelSensitivity = 0.5
	IntraFuelSensitivity = 0.5
	InitialVessels = 100
}

# B) DEFINITION OF A VESSEL
# Bi) Define vessel node "vessel_ice_oil" below.
Vessel "vessel_ice_oil" {
	PowerSystem = PowerSystem("ice_oil")
	Route = Route("route")
	NominalCapacity = 8000
	Tanks = [Tank("main_oil")]
	PropulsionLoad = 10
}


# Define and assign attributes of the node "vessel_ice_oil" 
# Above, edit the vessel node so that each attribute and its value is written within the curly
# brackets of the "vessel_ice_oil" node (i.e. PowerSystem, Route, Finance etc.). 


# Bii) Define PowerSystem below.
PowerSystem "ice_oil" {
	Propulsion = Converter("propulsion_ice_oil")
	Electrical = Converter("electrical_ice_oil")
	Heat = Converter("heat_boiler_oil")
}


# Define the node "propulsion_ice_oil" below.
Converter "propulsion_ice_oil" {
	PowerCapacity = 50
	MainFuelTypes = OIL
	Efficiency = 0.5
}

# Define the node "electrical_ice_oil" below.

Converter "electrical_ice_oil" {
	PowerCapacity = 10
	MainFuelTypes = OIL
	Efficiency = 0.5
}

# Define the node "heat_boiler_oil" below. 

Converter "heat_boiler_oil" {
	PowerCapacity = 5
	MainFuelTypes = OIL
	Efficiency = 0.5
}

# Biii) DEFINITION OF NODES THAT WERE INTRODUCED IN THE DEFINITION OF THE NODE "vessel_ice_oil".
# Define the node "main_oil" below.

Tank "main_oil" {
	FuelTypes = OIL
	Size = 9000
}

# Define the node "route" below.

Route "route" {
	RouteType = REGIONAL_TRIP 
	Ports = [Port("port")] 
	TimeAtSea = 0.75
	ConditionDistribution = [1.0]
	Speeds = [10]
}

# C) DEFINITION OF A PORT
# Define the node "port" below.

Port "port" {	
	set_bunker_price_overwrite("heavy_fuel_oil", 250)
	set_bunker_wtt_overwrite("heavy_fuel_oil", "carbon_dioxide", 0.62)
}


# D) DEFINITION OF A FUEL
# Define the node "heavy_fuel_oil" below.

# Define the fuel node "heavy_fuel_oil" below.		

Fuel "heavy_fuel_oil" {	
	FuelType = OIL
	LiquidMarket = TRUE
	LowerHeatingValue = 41.2
	MassDensity = 0.9

	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}

# E) DEFINITION OF A EMISSION

Emission "carbon_dioxide" {
	GlobalWarmingPotential = 1
}

Emission "methane" {
	GlobalWarmingPotential = 25
}

Emission "nitrous_oxide" {
	GlobalWarmingPotential = 273
}


# F) DEFINITION OF OUTPUT
# The Plot node tells Navigate which plots to produce and where to save them.
# Directory points at the "plots" subfolder; each add_plot(...) selects one plot.

Plot "plots" {
	Directory = "./plots/"

	add_plot("global_emission_absolute")
	add_plot("global_fuel_consumed")
	add_plot("port_bunker_price")
}


# END OF NAV FILE