# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# EU ETS - absolute price on CO2-equivalent burned on board, no free allowance.
#
# The coverage fractions are applied PER LEG, not to the round trip. Both legs
# here are inter-jurisdiction, so both count at 50%. Port stays are classified
# by their own port, so Rotterdam counts in full and San Antonio not at all.

Regulation "eu_ets" {
	Measure = ABSOLUTE
	Scheme = INDIVIDUAL
	Scope = TTW
	IncludeSlip = FALSE   # methane slip is carried in the TTW methane factors
	Emissions = [Emission("carbon_dioxide"), Emission("methane"), Emission("nitrous_oxide")]
	Fuels = Fuel("*")

	# Rotterdam is the only EU port on this route
	Jurisdiction = [Port("rotterdam")]
	IntraFraction = 1     # both ends in the EU
	InterFraction = 0.5   # one end in the EU
	ExtraFraction = 0     # neither end in the EU

	RemedialCost = <Forecast("eu_ets_carbon_credit_price") * Forecast("eu_ets_maritime_phase_in")>

	# no free allocation: every covered ton is paid for
	set_vessel_threshold("*", 0.)
	set_include_vessel("*", TRUE)

	set_global_warming_potential("carbon_dioxide", 1)
	set_global_warming_potential("methane", 28)
	set_global_warming_potential("nitrous_oxide", 265)

	# Emission factors follow MRV Maritime Regulation Annex I. Bio and electro
	# fuels are assumed to meet the >65% criterion, so are zero-rated for CO2 but
	# still take "highest in class" methane and nitrous oxide.
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", Variable("eu_default_diesel_carbon_dioxide"))
	set_fuel_ttw("fossil_fuel_oil", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("fossil_fuel_oil", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)

	set_fuel_ttw("liquefied_natural_gas", "carbon_dioxide", Variable("eu_default_methane_carbon_dioxide"))
	set_fuel_ttw("liquefied_natural_gas", "methane", <Forecast("eu_default_methane_slip") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("liquefied_natural_gas", "nitrous_oxide", <Variable("eu_default_methane_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)

	set_fuel_ttw("methanol_electro", "carbon_dioxide", 0)
	set_fuel_ttw("methanol_electro", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("methanol_electro", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)

	set_fuel_ttw("methanol_bio", "carbon_dioxide", 0)
	set_fuel_ttw("methanol_bio", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("methanol_bio", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)

	set_fuel_ttw("ammonia_electro", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_electro", "methane", <Variable("eu_default_diesel_ice_methane") * Forecast("eu_ets_ghg_phase_in")>)
	set_fuel_ttw("ammonia_electro", "nitrous_oxide", <Variable("eu_default_diesel_ice_nitrous_oxide") * Forecast("eu_ets_ghg_phase_in")>)
}
