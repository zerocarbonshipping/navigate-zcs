# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------------- FUEL EU --------------------------------------------- 
#
# This block represents the FuelEU Maritime regulation, which limits GHG intensity of fuels 
# used in EU waters. It applies fully to the ships in the Baltics.
#
# The policy promotes low-emission fuels like bio-methanol and penalizes fossil fuels, 
# helping simulate regulatory impact on fuel choice and compliance costs.
#
# ---------------------------------------------------------------------------------------

Regulation "fuel_eu" {

	Measure = INTENSITY
	Scheme = FLEXIBLE
	
	Scope = WTW
	IncludeSlip = FALSE # accounted for through TTW methane emission factors

	Emissions = [Emission("carbon_dioxide"), Emission("methane"), Emission("nitrous_oxide")]
	Fuels = Fuel("*")
	
	IntraFraction = 1
	InterFraction = 0.5
	ExtraFraction = 0
	
	Jurisdiction = [Port("helsinki"), Port("stockholm"), Port("gdansk"), Port("tallinn")]
	
	RemedialCost = Variable("fuel_eu_remedial_cost")
	SharedThreshold = Forecast("fuel_eu_target_reduction")
	
	# FuelEU applies to both domestic and international vessels that enter or operate in the EU
	set_include_vessel("*", TRUE)
	
	# Global warming potentials
	set_global_warming_potential("carbon_dioxide", 1)
	set_global_warming_potential("methane", 25)
	set_global_warming_potential("nitrous_oxide", 298)
	
	# LSFO
	set_fuel_wtt("fossil_fuel_oil", "*", 0) # this overwrites the Navigate calculation of WTT
	set_fuel_wtt("fossil_fuel_oil", "carbon_dioxide", Variable("fuel_eu_default_wtt_fossil_fuel_oil"))
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", Variable("eu_default_diesel_carbon_dioxide"))
	set_fuel_ttw("fossil_fuel_oil", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("fossil_fuel_oil", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
	
	# e-ammonia
	# since e-fuels require certified actual values under FuelEU and has no WTT defaults, we use the dynamically calculated Navigate values
	set_fuel_ttw("ammonia_electro", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_electro", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("ammonia_electro", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
}
