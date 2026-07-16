# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "gas_carrier_100k_cbm" {

	# vessel types
	Vessels = [
		Vessel("gas_carrier_100k_cbm_ice_ammonia"),
		Vessel("gas_carrier_100k_cbm_ice_methane"),
		Vessel("gas_carrier_100k_cbm_ice_methanol"),
		Vessel("gas_carrier_100k_cbm_ice_oil")
	]
	
	# initial conditions
	InitialVessels = Variable("initial_vessels_gas_carrier_100k_cbm")
	
	InitialSplit = [
		0.000,
		0.655,
		0.000,
		0.345
	]
	
	InitialAgeDistribution = [
		0,
		Curve("age_dist_gas_carrier_100k_cbm_methane"),
		0,
		Curve("age_dist_gas_carrier_100k_cbm_oil")
	]
	
	
	# trade growth
	TradeGrowth = Forecast("trade_growth_gas_carrier")
	
	# orderbooks
	Orderbooks = [
		Forecast("orderbook_gas_carrier_100k_cbm_ammonia"),
		Forecast("orderbook_gas_carrier_100k_cbm_methane"),
		Forecast("orderbook_gas_carrier_100k_cbm_methanol"),
		Forecast("orderbook_gas_carrier_100k_cbm_oil")
	]

	# technologies
	Technologies = [
		Technology("air_lubrication_gas_carrier_100k_cbm"),
		Technology("cargo_systems_gas_carrier_100k_cbm"),
		Technology("exhaust_gas_boiler_ae_gas_carrier_100k_cbm"),
		Technology("flettner_rotor_gas_carrier_100k_cbm"),
		Technology("hull_painting_gas_carrier_100k_cbm"),
		Technology("lighting_system_gas_carrier_100k_cbm"),
		Technology("propeller_improvement_devices_gas_carrier_100k_cbm"),
		Technology("variable_frequency_drive_gas_carrier_100k_cbm")
	]

	set_initial_technology_share("*", "cargo_systems_gas_carrier_100k_cbm", Curve("uptake_cargo_systems_gas_carrier_100k_cbm"))
	set_initial_technology_share("*", "exhaust_gas_boiler_ae_gas_carrier_100k_cbm", Curve("uptake_exhaust_gas_boiler_ae_gas_carrier_100k_cbm"))
	set_initial_technology_share("*", "hull_painting_gas_carrier_100k_cbm", Curve("uptake_hull_painting_gas_carrier_100k_cbm"))
	set_initial_technology_share("*", "lighting_system_gas_carrier_100k_cbm", Curve("uptake_lighting_system_gas_carrier_100k_cbm"))
	set_initial_technology_share("*", "propeller_improvement_devices_gas_carrier_100k_cbm", Curve("uptake_propeller_improvement_devices_gas_carrier_100k_cbm"))
	set_initial_technology_share("*", "variable_frequency_drive_gas_carrier_100k_cbm", Curve("uptake_variable_frequency_drive_gas_carrier_100k_cbm"))

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.6
}
