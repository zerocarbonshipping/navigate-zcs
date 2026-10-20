# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "roro_7000_ceu" {

	# vessel types
	Vessels = [
		Vessel("roro_7000_ceu_ice_ammonia"),
		Vessel("roro_7000_ceu_ice_methane"),
		Vessel("roro_7000_ceu_ice_methanol"),
		Vessel("roro_7000_ceu_ice_oil")
	]
	
	# initial conditions
	InitialVessels = Variable("initial_vessels_roro_7000_ceu")
	
	InitialSplit = [
		0.000,
		0.135,
		0.000,
		0.865
	]
	
	InitialAgeDistribution = [
		0,
		Curve("age_dist_roro_7000_ceu_methane"),
		0,
		Curve("age_dist_roro_7000_ceu_oil")
	]
	
	
	# trade growth
	TradeGrowth = Forecast("trade_growth_roro")
	
	# orderbooks
	Orderbooks = [
		Forecast("orderbook_roro_7000_ceu_ammonia"),
		Forecast("orderbook_roro_7000_ceu_methane"),
		Forecast("orderbook_roro_7000_ceu_methanol"),
		Forecast("orderbook_roro_7000_ceu_oil")
	]

	# technologies
	Technologies = [
		Technology("air_lubrication_roro_7000_ceu"),
		Technology("exhaust_gas_boiler_ae_roro_7000_ceu"),
		Technology("flettner_rotor_roro_7000_ceu"),
		Technology("hull_painting_roro_7000_ceu"),
		Technology("lighting_system_roro_7000_ceu"),
		Technology("propeller_improvement_devices_roro_7000_ceu"),
		Technology("variable_frequency_drive_roro_7000_ceu")
	]

	set_initial_technology_share("*", "exhaust_gas_boiler_ae_roro_7000_ceu", Curve("uptake_exhaust_gas_boiler_ae_roro_7000_ceu"))
	set_initial_technology_share("*", "hull_painting_roro_7000_ceu", Curve("uptake_hull_painting_roro_7000_ceu"))
	set_initial_technology_share("*", "lighting_system_roro_7000_ceu", Curve("uptake_lighting_system_roro_7000_ceu"))
	set_initial_technology_share("*", "propeller_improvement_devices_roro_7000_ceu", Curve("uptake_propeller_improvement_devices_roro_7000_ceu"))
	set_initial_technology_share("*", "variable_frequency_drive_roro_7000_ceu", Curve("uptake_variable_frequency_drive_roro_7000_ceu"))

	# speed management
    AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.2
}
