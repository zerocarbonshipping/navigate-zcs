# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Regulation "eu_ets" {

	Measure = ABSOLUTE
	Scheme = INDIVIDUAL

	Scope = TTW
	IncludeSlip = FALSE # accounted for through TTW methane emission factors

	Emissions = [Emission("carbon_dioxide"), Emission("methane"), Emission("nitrous_oxide")]
	Fuels = Fuel("*")
	
	IntraFraction = 1
	InterFraction = 0.5
	ExtraFraction = 0
	
	Jurisdiction = [Port("port_europe")]
	
	RemedialCost = <Forecast("eu_ets_carbon_credit_price") * Forecast("eu_ets_maritime_phase_in")>
	set_vessel_threshold("*", 0.)
	
	# EU ETS applies to both domestic and international vessels that enter or operate in the EU
	set_include_vessel("*", TRUE)
	
	# global warming potentials ---------------------------------------------------------------------------------------------------------------------
	set_global_warming_potential("carbon_dioxide", 1)
	set_global_warming_potential("methane", 28)
	set_global_warming_potential("nitrous_oxide", 265)
	
	# default emission factors ----------------------------------------------------------------------------------------------------------------------
	# EU ETS emission factors are based on MRV Maritime Regulation Annex I.
	# All bio and electro fuels are assumed to have a proven >65% reduction relative to LSFO and thus meet the
	# criteria for "zero-rated" which means the fuel is classified with zero carbon dioxide emissions.
	# Blue ammmonia is assumed to have a proven >70% reduction and thus be classed as a "low-carbon fuel" which
	# also meets the crtieria for being "zero-rated" (RED Implemementing Regulation 2018/2066 Article 23c (c)).
	# The "zero-rated" does not apply to methane and nitrous oxide which for bio and electro are all defined
	# as TBM (to be measured) and for blue either TBM or N/A (not applicable). In this case they should use the
	# "highest in class" value which for all fuels correspond to methane emissions of 0.00005 and nitrous oxide
	# emissions of 0.00018.
	
	# fuel oil / diesel -----------------------------------------------------------------------------------------------------------------------------
	# LSFO
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", Variable("eu_default_diesel_carbon_dioxide"))
	set_fuel_ttw("fossil_fuel_oil", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("fossil_fuel_oil", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# FAME
	set_fuel_ttw("fatty_acid_methyl_ester", "carbon_dioxide", 0)
	set_fuel_ttw("fatty_acid_methyl_ester", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("fatty_acid_methyl_ester", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	
	# e-diesel
	set_fuel_ttw("diesel_electro", "carbon_dioxide", 0)
	set_fuel_ttw("diesel_electro", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("diesel_electro", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# natural gas / methane -------------------------------------------------------------------------------------------------------------------------
	# LNG
	set_fuel_ttw("liquefied_natural_gas", "carbon_dioxide", Variable("eu_default_methane_carbon_dioxide"))
	set_fuel_ttw("liquefied_natural_gas", "methane", <Forecast("eu_default_methane_slip") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("liquefied_natural_gas", "nitrous_oxide", <Variable("eu_default_methane_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# bio-methane
	set_fuel_ttw("methane_bio", "carbon_dioxide", 0)
	set_fuel_ttw("methane_bio", "methane", <Forecast("eu_default_methane_slip") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("methane_bio", "nitrous_oxide", <Variable("eu_default_methane_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# e-methane
	set_fuel_ttw("methane_electro", "carbon_dioxide", 0)
	set_fuel_ttw("methane_electro", "methane",  <Forecast("eu_default_methane_slip") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("methane_electro", "nitrous_oxide", <Variable("eu_default_methane_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# methanol --------------------------------------------------------------------------------------------------------------------------------------
	# bio-methanol
	set_fuel_ttw("methanol_bio", "carbon_dioxide", 0)
	set_fuel_ttw("methanol_bio", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("methanol_bio", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# e-methanol
	set_fuel_ttw("methanol_electro", "carbon_dioxide", 0)
	set_fuel_ttw("methanol_electro", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("methanol_electro", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# ammonia ---------------------------------------------------------------------------------------------------------------------------------------
	# blue ammonia
	set_fuel_ttw("ammonia_blue", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_blue", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("ammonia_blue", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
	
	# e-ammonia
	set_fuel_ttw("ammonia_electro", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_electro", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("ammonia_electro", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
}
