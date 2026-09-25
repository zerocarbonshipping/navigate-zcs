# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUELEU MARITIME - caps WTW greenhouse gas intensity, tightening over time.
#
# The e-fuels get no set_fuel_wtt line below on purpose: Navigate calculates
# their upstream intensity from the production chain in regions.inc, so the
# power price at each site feeds their FuelEU score. The fossil fuels and
# bio-methanol instead use the regulation's own defaults.
#
# Same coverage geography as eu_ets.inc.

Regulation "fuel_eu" {
	Measure = INTENSITY
	Scheme = FLEXIBLE     # pooled and banked across years, unlike the ETS
	Scope = WTW
	IncludeSlip = FALSE   # methane slip is carried in the TTW methane factors
	Emissions = [Emission("carbon_dioxide"), Emission("methane"), Emission("nitrous_oxide")]
	Fuels = Fuel("*")

	Jurisdiction = [Port("rotterdam")]
	IntraFraction = 1
	InterFraction = 0.5
	ExtraFraction = 0

	RemedialCost = Variable("fuel_eu_remedial_cost")

	set_vessel_threshold("*", Forecast("fuel_eu_target_reduction"))
	set_include_vessel("*", TRUE)

	set_global_warming_potential("carbon_dioxide", 1)
	set_global_warming_potential("methane", 25)
	set_global_warming_potential("nitrous_oxide", 298)

	# ---- fossil fuel oil: regulation default WTT ----
	set_fuel_wtt("fossil_fuel_oil", "*", 0)
	set_fuel_wtt("fossil_fuel_oil", "carbon_dioxide", Variable("fuel_eu_default_wtt_fossil_fuel_oil"))
	set_fuel_ttw("fossil_fuel_oil", "carbon_dioxide", Variable("eu_default_diesel_carbon_dioxide"))
	set_fuel_ttw("fossil_fuel_oil", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("fossil_fuel_oil", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))

	# ---- LNG ----
	set_fuel_wtt("liquefied_natural_gas", "*", 0)
	set_fuel_wtt("liquefied_natural_gas", "carbon_dioxide", Variable("fuel_eu_default_wtt_liquefied_natural_gas"))
	set_fuel_ttw("liquefied_natural_gas", "carbon_dioxide", Variable("eu_default_methane_carbon_dioxide"))
	set_fuel_ttw("liquefied_natural_gas", "methane", Forecast("eu_default_methane_slip"))
	set_fuel_ttw("liquefied_natural_gas", "nitrous_oxide", Variable("eu_default_methane_ice_nitrous_oxide"))

	# ---- bio-methanol: regulation default WTT ----
	set_fuel_wtt("methanol_bio", "*", 0)
	set_fuel_wtt("methanol_bio", "carbon_dioxide", Variable("fuel_eu_default_wtt_methanol_bio"))
	set_fuel_ttw("methanol_bio", "carbon_dioxide", Variable("fuel_eu_default_methanol_ice_carbon_dioxide"))
	set_fuel_ttw("methanol_bio", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("methanol_bio", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))

	# ---- e-methanol: WTT calculated, not set ----
	set_fuel_ttw("methanol_electro", "carbon_dioxide", Variable("fuel_eu_default_methanol_ice_carbon_dioxide"))
	set_fuel_ttw("methanol_electro", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("methanol_electro", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))

	# ---- e-ammonia: WTT calculated; no carbon in the molecule ----
	set_fuel_ttw("ammonia_electro", "carbon_dioxide", 0)
	set_fuel_ttw("ammonia_electro", "methane", Variable("eu_default_diesel_ice_methane"))
	set_fuel_ttw("ammonia_electro", "nitrous_oxide", Variable("eu_default_diesel_ice_nitrous_oxide"))
}
