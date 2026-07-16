# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

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
	
	Jurisdiction = [Port("port_europe")]
	
	RemedialCost = Variable("fuel_eu_remedial_cost")
	SharedThreshold = Forecast("fuel_eu_target_reduction")
	
	# FuelEU applies to both domestic and international vessels that enter or operate in the EU
	set_include_vessel("*", TRUE)
	
	# global warming potentials -------------------------------------------------------------------------------------
	set_global_warming_potential("carbon_dioxide", 1)
	set_global_warming_potential("methane", 25)
	set_global_warming_potential("nitrous_oxide", 298)
	
	# fuel oil / diesel ---------------------------------------------------------------------------------------------
	# LSFO
	set_fuel_wtt("fossil_fuel_oil", "*", 0) # this overwrites the Navigate calculation of WTT
	set_fuel_wtt("fossil_fuel_oil", "carbon_dioxide", Variable("fuel_eu_default_wtt_fossil_fuel_oil"))
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", Variable("eu_default_diesel_carbon_dioxide"))
	set_fuel_ttw("fossil_fuel_oil", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("fossil_fuel_oil", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
	
	# FAME
	set_fuel_wtt("fatty_acid_methyl_ester", "*", 0)	# this overwrites the Navigate calculation of WTT
	set_fuel_wtt("fatty_acid_methyl_ester", "carbon_dioxide", Variable("fuel_eu_default_wtt_fatty_acid_methyl_ester"))
	set_fuel_ttw("fatty_acid_methyl_ester", "carbon_dioxide", Variable("fuel_eu_default_fatty_acid_methyl_ester_ice_carbon_dioxide"))
	set_fuel_ttw("fatty_acid_methyl_ester", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("fatty_acid_methyl_ester", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
	
	# bio-oil
	# since bio-oils are undefined in FuelEU and would require certified actual values we assume dynamically calculated Navigate values
	
	# e-diesel
	# since e-fuels require certified actual values under FuelEU and has no WTT defaults, we use the dynamically calculated Navigate values
	set_fuel_ttw("diesel_electro", "carbon_dioxide", Variable("fuel_eu_default_diesel_ice_carbon_dioxide"))
	set_fuel_ttw("diesel_electro", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("diesel_electro", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))

	# natural gas / methane -----------------------------------------------------------------------------------------
	# LNG
	set_fuel_wtt("liquefied_natural_gas", "*", 0) # this overwrites the Navigate calculation of WTT
	set_fuel_wtt("liquefied_natural_gas", "carbon_dioxide", Variable("fuel_eu_default_wtt_liquefied_natural_gas"))
	set_fuel_ttw("liquefied_natural_gas", "carbon_dioxide", Variable("eu_default_methane_carbon_dioxide"))
	set_fuel_ttw("liquefied_natural_gas", "methane", Forecast("eu_default_methane_slip"))
	set_fuel_ttw("liquefied_natural_gas", "nitrous_oxide", Variable("eu_default_methane_ice_nitrous_oxide"))
	
	# bio-methane
	set_fuel_wtt("methane_bio", "*", 0)	 # this overwrites the Navigate calculation of WTT																			
	set_fuel_wtt("methane_bio", "carbon_dioxide", Variable("fuel_eu_default_wtt_methane_bio"))
	set_fuel_ttw("methane_bio", "carbon_dioxide", Variable("eu_default_methane_carbon_dioxide"))
	set_fuel_ttw("methane_bio", "methane", Forecast("eu_default_methane_slip"))
	set_fuel_ttw("methane_bio", "nitrous_oxide", Variable("eu_default_methane_ice_nitrous_oxide"))
	
	# e-methane
	# since e-fuels require certified actual values under FuelEU and has no WTT defaults, we use the dynamically calculated Navigate values
	set_fuel_ttw("methane_electro", "carbon_dioxide", Variable("eu_default_methane_carbon_dioxide"))
	set_fuel_ttw("methane_electro", "methane", Forecast("eu_default_methane_slip"))
	set_fuel_ttw("methane_electro", "nitrous_oxide", Variable("eu_default_methane_ice_nitrous_oxide"))
	
	# methanol ------------------------------------------------------------------------------------------------------
	# bio-methanol
	set_fuel_wtt("methanol_bio", "*", 0) # this overwrites the Navigate calculation of WTT
	set_fuel_wtt("methanol_bio", "carbon_dioxide", Variable("fuel_eu_default_wtt_methanol_bio"))
	set_fuel_ttw("methanol_bio", "carbon_dioxide", Variable("fuel_eu_default_methanol_ice_carbon_dioxide"))
	set_fuel_ttw("methanol_bio", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("methanol_bio", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))

	# e-methanol
	# since e-fuels require certified actual values under FuelEU and has no WTT defaults, we use the dynamically calculated Navigate values
	set_fuel_ttw("methanol_electro", "carbon_dioxide", Variable("fuel_eu_default_methanol_ice_carbon_dioxide"))
	set_fuel_ttw("methanol_electro", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("methanol_electro", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
	
	# ammonia -------------------------------------------------------------------------------------------------------
	# blue ammonia
	# since blue fuels require certified actual values under FuelEU and has no WTT defaults, we use the dynamically calculated Navigate values
	set_fuel_ttw("ammonia_blue", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_blue", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("ammonia_blue", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))

	# e-ammonia
	# since e-fuels require certified actual values under FuelEU and has no WTT defaults, we use the dynamically calculated Navigate values
	set_fuel_ttw("ammonia_electro", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_electro", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("ammonia_electro", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
}
