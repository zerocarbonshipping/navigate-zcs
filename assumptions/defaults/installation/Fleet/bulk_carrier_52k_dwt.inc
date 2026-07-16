# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "bulk_carrier_52k_dwt" {

    # vessel types
	Vessels = [
		Vessel("bulk_carrier_52k_dwt_ice_ammonia"),
		Vessel("bulk_carrier_52k_dwt_ice_methane"),
 		Vessel("bulk_carrier_52k_dwt_ice_methanol"),
		Vessel("bulk_carrier_52k_dwt_ice_oil")
	]

	# initial conditions
	InitialVessels = Variable("initial_vessels_bulk_carrier_52k_dwt")

	InitialSplit = [
		0.000,
		0.000,
		0.000,
		1.000
	]

	InitialAgeDistribution = [
		0,
		0,
		0,
		Curve("age_dist_bulk_carrier_52k_dwt_oil")
	]


	# trade growth
	TradeGrowth = Forecast("trade_growth_bulk_carrier")

	# orderbook
	Orderbooks = [
		Forecast("orderbook_bulk_carrier_52k_dwt_ammonia"),
		Forecast("orderbook_bulk_carrier_52k_dwt_methane"),
		Forecast("orderbook_bulk_carrier_52k_dwt_methanol"),
		Forecast("orderbook_bulk_carrier_52k_dwt_oil")
	]

	# technologies
	Technologies = [
		Technology("air_lubrication_bulk_carrier_handy"),
		Technology("exhaust_gas_boiler_ae_bulk_carrier_handy"),
		Technology("flettner_rotor_bulk_carrier_handy"),
		Technology("hull_painting_bulk_carrier_handy"),
		Technology("lighting_system_bulk_carrier_handy"),
		Technology("propeller_improvement_devices_bulk_carrier_handy"),
		Technology("variable_frequency_drive_bulk_carrier_handy")
	]

	set_initial_technology_share("*", "exhaust_gas_boiler_ae_bulk_carrier_handy", Curve("uptake_exhaust_gas_boiler_ae_bulk_carrier_handy"))
	set_initial_technology_share("*", "hull_painting_bulk_carrier_handy", Curve("uptake_hull_painting_bulk_carrier_handy"))
	set_initial_technology_share("*", "lighting_system_bulk_carrier_handy", Curve("uptake_lighting_system_bulk_carrier_handy"))
	set_initial_technology_share("*", "propeller_improvement_devices_bulk_carrier_handy", Curve("uptake_propeller_improvement_devices_bulk_carrier_handy"))
	set_initial_technology_share("*", "variable_frequency_drive_bulk_carrier_handy", Curve("uptake_variable_frequency_drive_bulk_carrier_handy"))

	# fuel conversions
	set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 15.5e6)
	set_fuel_conversion_cost("*ice_oil*", "*ice_ammonia*", 21e6)
	set_fuel_conversion_cost("*ice_methane*", "*ice_ammonia*", 12.3e6)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.4
}
