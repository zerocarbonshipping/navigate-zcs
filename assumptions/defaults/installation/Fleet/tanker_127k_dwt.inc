# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "tanker_127k_dwt" {

	# vessel types
	Vessels = [
		Vessel("tanker_127k_dwt_ice_ammonia"),
		Vessel("tanker_127k_dwt_ice_methane"),
		Vessel("tanker_127k_dwt_ice_methanol"),
		Vessel("tanker_127k_dwt_ice_oil")
	]
	
	# initial conditions
	InitialVessels = Variable("initial_vessels_tanker_127k_dwt")
	
	InitialSplit = [
		0.000,
		0.032,
		0.000,
		0.968
	]
	
	InitialAgeDistribution = [
		0,
		Curve("age_dist_tanker_127k_dwt_methane"),
		0,
		Curve("age_dist_tanker_127k_dwt_oil")
	]
	

	# trade growth
	TradeGrowth = Forecast("trade_growth_tanker")

	# orderbook
	Orderbooks = [
		Forecast("orderbook_tanker_127k_dwt_ammonia"),
		Forecast("orderbook_tanker_127k_dwt_methane"),
		Forecast("orderbook_tanker_127k_dwt_methanol"),
		Forecast("orderbook_tanker_127k_dwt_oil")
	]

	# technologies
	Technologies = [
		Technology("air_lubrication_tanker_100k_dwt"),
		Technology("cargo_systems_tanker_100k_dwt"),
		Technology("exhaust_gas_boiler_ae_tanker_100k_dwt"),
		Technology("flettner_rotor_tanker_100k_dwt"),
		Technology("hull_painting_tanker_100k_dwt"),
		Technology("lighting_system_tanker_100k_dwt"),
		Technology("propeller_improvement_devices_tanker_100k_dwt"),
		Technology("variable_frequency_drive_tanker_100k_dwt")
	]

	set_initial_technology_share("*", "cargo_systems_tanker_100k_dwt", Curve("uptake_cargo_systems_tanker_100k_dwt"))
	set_initial_technology_share("*", "exhaust_gas_boiler_ae_tanker_100k_dwt", Curve("uptake_exhaust_gas_boiler_ae_tanker_100k_dwt"))
	set_initial_technology_share("*", "hull_painting_tanker_100k_dwt", Curve("uptake_hull_painting_tanker_100k_dwt"))
	set_initial_technology_share("*", "lighting_system_tanker_100k_dwt", Curve("uptake_lighting_system_tanker_100k_dwt"))
	set_initial_technology_share("*", "propeller_improvement_devices_tanker_100k_dwt", Curve("uptake_propeller_improvement_devices_tanker_100k_dwt"))
	set_initial_technology_share("*", "variable_frequency_drive_tanker_100k_dwt", Curve("uptake_variable_frequency_drive_tanker_100k_dwt"))

	# fuel conversions
	set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 18.2e6)
	set_fuel_conversion_cost("*ice_oil*", "*ice_ammonia*", 28.3e6)
	set_fuel_conversion_cost("*ice_methane*", "*ice_ammonia*", 19.4e6)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.6
}
