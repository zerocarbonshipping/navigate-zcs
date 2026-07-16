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
Fleet "container_fleet" {
	Vessels = [Vessel("container_ice_oil"), Vessel("container_ice_methane")]
	InterFuelSensitivity = 0.5
	IntraFuelSensitivity = 0.5
	InitialVessels = 100
	TradeGrowth = 0.05
}

# Aii) Bulk carrier fleet
# Paste the copy of the Fleet node "container_fleet" below, and make edits as
# described in the tutorial:
Fleet "bulk_fleet" {
	Vessels = [Vessel("bulk_ice_methanol"), Vessel("bulk_ice_ammonia")]
	InterFuelSensitivity = 0.5
	IntraFuelSensitivity = 0.5
	InitialVessels = 100
	TradeGrowth = 0.05
}


# B) DEFINITION OF ALL FOUR VESSELS
# Bi) Definition of fuel oil vessel
# Change the the value assigned to the attribute Tanks below.

Vessel "container_ice_oil" {
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


# Bii) DEFINITION OF METHANE VESSEL
# This definition has the same structure as the definition of the fuel oil vessel, but has
# different assigned values.
#
# Define Vessel "container_ice_methane", Powersystem "ice_methane", Converter "propulsion_ice_methane", 
# Converter "electrical_ice_methane", Converter "heat_boiler_methane".
#
# Paste the nodes from section Bi) below.

Vessel "container_ice_methane" {
	PowerSystem = PowerSystem("ice_methane")
	Route = Route("route")
	NominalCapacity = 8000
	Tanks = [Tank("main_methane"), Tank("pilot_oil")]
	PropulsionLoad = 10
}

# Same as in tutorial 1.
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

# Biii) DEFINITION OF METHANOL VESSEL
#
# Define Vessel "bulk_ice_methanol", Powersystem "ice_methanol_bulk", Converter "propulsion_ice_methanol_bulk", 
# Converter "electrical_ice_methanol_bulk", Converter "heat_boiler_methanol_bulk".
#
# Paste the nodes from section Bi) below.
Vessel "bulk_ice_methanol" {
	PowerSystem = PowerSystem("ice_methanol")
	Route = Route("route")
	NominalCapacity = 8000
	Tanks = [Tank("main_methanol"), Tank("pilot_oil")]
	PropulsionLoad = 10
}

# Same as in tutorial 1.
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

# Biv) DEFINITION OF AMMONIA VESSEL
#
# Define Vessel "bulk_ice_ammonia", Powersystem "ice_ammonia_bulk", Converter "propulsion_ice_ammonia_bulk", 
# Converter "electrical_ice_ammonia_bulk", Converter "heat_boiler_ammonia_bulk".
#
# Paste the nodes from section Bi) below.
Vessel "bulk_ice_ammonia" {
	PowerSystem = PowerSystem("ice_ammonia")
	Route = Route("route")
	NominalCapacity = 8000
	Tanks = [Tank("main_ammonia"), Tank("pilot_oil")]
	PropulsionLoad = 10
}

# Same as in tutorial 1.
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
Tank "pilot_oil" {
	FuelTypes = OIL
	Size = 2000
}

# Cii) DEFINITION OF METHANE TANK
# Define Tank "main_methane".
# Paste the node Tank "main_oil" from section C) below.
Tank "main_methane" {
	FuelTypes = METHANE
	Size = 9000
}


# Ciii) DEFINITION OF METHANOL TANK
# Define Tank "main_methanol".
# Paste the node Tank "main_oil" from section C) below.
Tank "main_methanol" {
	FuelTypes = METHANOL
	Size = 9000
}


# Civ) DEFINITION OF AMMONIA TANK
# Define Tank "main_ammonia".
# Paste the node Tank "main_oil" from section C) below.
Tank "main_ammonia" {
	FuelTypes = AMMONIA
	Size = 9000
}


# D) DEFINITION OF THE PORT
# Definition of the node "port" and BunkerLogistics from tutorial 1 below:

Port "port" {
	set_bunker_price_overwrite("heavy_fuel_oil", 120)
	set_bunker_wtt_overwrite("heavy_fuel_oil", "carbon_dioxide", 0.62)
}


BunkerLogistics {
	LiquidMarketFuels = [Fuel("heavy_fuel_oil")]
}

Region "region" {
	# e-methane
	set_process_capex("methane_synthesis_electro", 100)
	set_process_energy("methane_synthesis_electro", 0.4)
	set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", -1)

	set_process_capex("methane_liquefaction_electro", 200)
	set_process_opex("methane_liquefaction_electro", 88)
	set_process_energy("methane_liquefaction_electro", 0.6)
	set_process_wtt("methane_liquefaction_electro", "carbon_dioxide", 0.5)


	# Bio-methanol
	set_process_capex("methanol_synthesis_bio_gasification", 180)
	set_process_opex("methanol_synthesis_bio_gasification", 100)
	set_process_energy("methanol_synthesis_bio_gasification", 0.52)

	set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", -1.35)
	set_process_wtt("methanol_synthesis_bio_gasification", "methane", 0.00005)
	set_process_wtt("methanol_synthesis_bio_gasification", "nitrous_oxide", 0.00018)

	# Blue ammonia
	set_process_capex("haber_bosch_ccs_integrated_blue", 200)
	set_process_opex("haber_bosch_ccs_integrated_blue", 50	) 
	set_process_energy("haber_bosch_ccs_integrated_blue", 0.25)
	
	set_feedstock_wtt("natural_gas", "carbon_dioxide", 0.11)
	set_feedstock_wtt("natural_gas", "methane", 0.0073)

	set_process_wtt("haber_bosch_ccs_integrated_blue", "carbon_dioxide", 0.180) 
}



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
Plant "plant_methane_electro" {
	Fuel = Fuel("methane_electro")
	Process = Process("methane_liquefaction_electro")
	Region = Region("region")
	Source = Source("renewable")
	Capacity = 1000
	LeadTime = 4
}

# define fuel and processes
# Define Fuel "methane_electro"
Fuel "methane_electro" {
	FuelType = METHANE
	LowerHeatingValue = 50
	MassDensity = 0.43

	set_ttw("carbon_dioxide", 2.75)
}

# Define Process "methane_liquefaction_electro"
Process "methane_liquefaction_electro" {
	Feeds = [Process("methane_synthesis_electro")]
	Conversions = [1]
}


# Define Process "methane_synthesis_electro"
Process "methane_synthesis_electro" {
	Feeds = [Feedstock("demineralized_water"), Feedstock("carbon_dioxide_biogenic")]
	Conversions = [4.5, 2.75]
}


# Define Feedstocks
Feedstock "demineralized_water" {
}

Feedstock "carbon_dioxide_biogenic" {
}


# Eiii) Definition of bio-methanol
# Paste the nodes "plant_methane_electro", Fuel "methane_electro", "methane_synthesis_electro", Feedstock "demineralized_water" and Feedstock "carbon_dioxide_biogenic"  from section Bi) below:
Plant "plant_methanol_bio_gasification" {
	Fuel = Fuel("methanol_bio")
	Process = Process("methanol_synthesis_bio_gasification")
	Region = Region("region")
	Source = Source("grid")
	Capacity = 1000
	LeadTime = 4
}

Fuel "methanol_bio" {
	FuelType = METHANOL
	LowerHeatingValue = 19.9
	MassDensity = 0.791

	set_ttw("carbon_dioxide", 1.38)
}

Process "methanol_synthesis_bio_gasification" {
	Feeds = [Feedstock("organic_wet_waste"), Feedstock("dry_wood_biomass")]
	Conversions = [1.21, 1.21]
}

Feedstock "organic_wet_waste" {	
}

Feedstock "dry_wood_biomass" {	
}


# Eiv) Definition of blue ammonia
# Paste the nodes "plant_methane_electro", Fuel "methane_electro", "methane_synthesis_electro", Feedstock "demineralized_water" and Feedstock "carbon_dioxide_biogenic"  from section Bii) below:
Plant "plant_ammonia_blue" {
	Fuel = Fuel("ammonia_blue")
	Process = Process("haber_bosch_ccs_integrated_blue")
	Region = Region("region")
	Source = Source("grid")
	Capacity = 1000
	LeadTime = 4
}

Fuel "ammonia_blue" {
	FuelType = AMMONIA
	LowerHeatingValue = 18.8
	MassDensity = 0.623
}


Process "haber_bosch_ccs_integrated_blue" {
	Feeds = [Process("nitrogen_air_seperation"), Feedstock("natural_gas")]
	Conversions = [0.64, 0.822]
}

Feedstock "natural_gas" {
}

Process "nitrogen_air_seperation" {
}

# Define energy sources "renewable" and "grid"
Source "renewable" {
	Dependency = CONNECTED
}


Source "grid" {
	Dependency = CONNECTED
}


# F) Definition of nodes related to fuel production
# Define the producer "engineering_procurement_construction_global"
Producer "engineering_procurement_construction_global" {
	Plants = [
		Plant("plant_methane_electro"),
		Plant("plant_methanol_bio_gasification"),
		Plant("plant_ammonia_blue")
	]
	
	FuelDemandSensitivity = 1.5
	FuelCostSensitivity = 0.5

	MaximumDevelopment = 10
}


# G) DEFINITION OF OUTPUT
# The Plot node tells Navigate which plots to produce and where to save them.
# Directory points at the "plots" subfolder; each add_plot(...) selects one plot.

Plot "plots" {
	Directory = "./plots/"

	add_plot("global_emission_absolute")
	add_plot("global_fuel_consumed")
	add_plot("plant_production_cost")
	add_plot("port_bunker_price")
}

# END OF NAV FILE