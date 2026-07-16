# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "container_1500_teu" {

	# vessel types
	Vessels = [
		Vessel("container_1500_teu_ice_ammonia"),
		Vessel("container_1500_teu_ice_methane"),
		Vessel("container_1500_teu_ice_methanol"),
		Vessel("container_1500_teu_ice_oil")
	]

	# initial conditions
	InitialVessels = Variable("initial_vessels_container_1500_teu")

	InitialSplit = [
		0.000,
		0.010,
		0.002,
		0.988
	]

	InitialAgeDistribution = [
		0,
		Curve("age_dist_container_1500_teu_methane"),
		Curve("age_dist_container_1500_teu_methanol"),
		Curve("age_dist_container_1500_teu_oil")
	]


	# trade growth
	TradeGrowth = Forecast("trade_growth_container_1500_teu")

	# orderbook
	Orderbooks = [
		Forecast("orderbook_container_1500_teu_ammonia"),
		Forecast("orderbook_container_1500_teu_methane"),
		Forecast("orderbook_container_1500_teu_methanol"),
		Forecast("orderbook_container_1500_teu_oil")
	]

	# technologies
	Technologies = [
		Technology("air_lubrication_container_3500_teu"),
		Technology("exhaust_gas_boiler_ae_container_3500_teu"),
		Technology("hull_painting_container_3500_teu"),
		Technology("kite_container_3500_teu"),
		Technology("lighting_system_container_3500_teu"),
		Technology("propeller_improvement_devices_container_3500_teu"),
		Technology("variable_frequency_drive_container_3500_teu")
	]

	set_initial_technology_share("*", "exhaust_gas_boiler_ae_container_3500_teu", Curve("uptake_exhaust_gas_boiler_ae_container_3500_teu"))
	set_initial_technology_share("*", "hull_painting_container_3500_teu", Curve("uptake_hull_painting_container_3500_teu"))
	set_initial_technology_share("*", "lighting_system_container_3500_teu", Curve("uptake_lighting_system_container_3500_teu"))
	set_initial_technology_share("*", "propeller_improvement_devices_container_3500_teu", Curve("uptake_propeller_improvement_devices_container_3500_teu"))
	set_initial_technology_share("*", "variable_frequency_drive_container_3500_teu", Curve("uptake_variable_frequency_drive_container_3500_teu"))

	# fuel conversions
	set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 10.3e6)
	set_fuel_conversion_cost("*ice_oil*", "*ice_ammonia*", 15.5e6)
	set_fuel_conversion_cost("*ice_methane*", "*ice_ammonia*", 17.5e6)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.5
}
