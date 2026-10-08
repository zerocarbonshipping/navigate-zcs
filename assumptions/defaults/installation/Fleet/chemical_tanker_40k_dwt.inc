# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from tanker_47k_dwt, owner to confirm (Ship Design & Technology).

Fleet "chemical_tanker_40k_dwt" {

	# vessel types
	Vessels = [
		Vessel("chemical_tanker_40k_dwt_ice_ammonia"),
		Vessel("chemical_tanker_40k_dwt_ice_methane"),
		Vessel("chemical_tanker_40k_dwt_ice_methanol"),
		Vessel("chemical_tanker_40k_dwt_ice_oil")
	]

	# initial conditions: initial vessels from the Assumptions record
	# vessels/new_segments_fleet_counts; the initial split is inherited from the parent, not
	# sourced; no public age distribution or orderbook exists for this segment, so none is set
	# (0) pending the fleet pipeline, see worklogs/vessels/new_segments/status.md
	InitialVessels = Variable("initial_vessels_chemical_tanker_40k_dwt")

	InitialSplit = [
		0.000,
		0.003,
		0.008,
		0.988
	]

	InitialAgeDistribution = [
		0,
		0,
		0,
		0
	]

	# trade growth
	TradeGrowth = Forecast("trade_growth_tanker")

	# orderbook
	Orderbooks = [
		0,
		0,
		0,
		0
	]

	# technologies: inherited from tanker_47k_dwt (shared tanker_35k_dwt nodes), pending the EE
	# applicability matrix for the new segments (Fleet Performance & EE)
	Technologies = [
		Technology("air_lubrication_tanker_35k_dwt"),
		Technology("cargo_systems_tanker_35k_dwt"),
		Technology("exhaust_gas_boiler_ae_tanker_35k_dwt"),
		Technology("flettner_rotor_tanker_35k_dwt"),
		Technology("hull_painting_tanker_35k_dwt"),
		Technology("lighting_system_tanker_35k_dwt"),
		Technology("propeller_improvement_devices_tanker_35k_dwt"),
		Technology("variable_frequency_drive_tanker_35k_dwt")
	]

	set_initial_technology_share("*", "cargo_systems_tanker_35k_dwt", Curve("uptake_cargo_systems_tanker_35k_dwt"))
	set_initial_technology_share("*", "exhaust_gas_boiler_ae_tanker_35k_dwt", Curve("uptake_exhaust_gas_boiler_ae_tanker_35k_dwt"))
	set_initial_technology_share("*", "hull_painting_tanker_35k_dwt", Curve("uptake_hull_painting_tanker_35k_dwt"))
	set_initial_technology_share("*", "lighting_system_tanker_35k_dwt", Curve("uptake_lighting_system_tanker_35k_dwt"))
	set_initial_technology_share("*", "propeller_improvement_devices_tanker_35k_dwt", Curve("uptake_propeller_improvement_devices_tanker_35k_dwt"))
	set_initial_technology_share("*", "variable_frequency_drive_tanker_35k_dwt", Curve("uptake_variable_frequency_drive_tanker_35k_dwt"))

	# fuel conversions: costs inherited unchanged from tanker_47k_dwt, not sourced for this
	# segment; pending the conversion-cost family
	set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 12.3e6)
	set_fuel_conversion_cost("*ice_oil*", "*ice_ammonia*", 18.7e6)
	set_fuel_conversion_cost("*ice_methane*", "*ice_ammonia*", 17.6e6)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.4
}
