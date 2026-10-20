# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "bulk_carrier_80k_dwt" {

    # vessel types		
	Vessels = [
		Vessel("bulk_carrier_80k_dwt_ice_ammonia"),
		Vessel("bulk_carrier_80k_dwt_ice_methane"),
 		Vessel("bulk_carrier_80k_dwt_ice_methanol"),
		Vessel("bulk_carrier_80k_dwt_ice_oil")
	]
	
	# initial conditions
	InitialVessels = Variable("initial_vessels_bulk_carrier_80k_dwt")
	
	InitialSplit = [
		0.000,
		0.001,
		0.000,
		0.999
	]
	
	InitialAgeDistribution = [
		0,
		Curve("age_dist_bulk_carrier_80k_dwt_methane"),
		0,
		Curve("age_dist_bulk_carrier_80k_dwt_oil")
	]
	
	
	# trade growth
	TradeGrowth = Forecast("trade_growth_bulk_carrier")
	
	# orderbook
	Orderbooks = [
		Forecast("orderbook_bulk_carrier_80k_dwt_ammonia"),
		Forecast("orderbook_bulk_carrier_80k_dwt_methane"),
		Forecast("orderbook_bulk_carrier_80k_dwt_methanol"),
		Forecast("orderbook_bulk_carrier_80k_dwt_oil")
	]

	# technologies
	Technologies = [
		Technology("air_lubrication_bulk_carrier_panamax"),
		Technology("exhaust_gas_boiler_ae_bulk_carrier_panamax"),
		Technology("flettner_rotor_bulk_carrier_panamax"),
		Technology("hull_painting_bulk_carrier_panamax"),
		Technology("lighting_system_bulk_carrier_panamax"),
		Technology("propeller_improvement_devices_bulk_carrier_panamax"),
		Technology("variable_frequency_drive_bulk_carrier_panamax")
	]

	set_initial_technology_share("*", "exhaust_gas_boiler_ae_bulk_carrier_panamax", Curve("uptake_exhaust_gas_boiler_ae_bulk_carrier_panamax"))
	set_initial_technology_share("*", "hull_painting_bulk_carrier_panamax", Curve("uptake_hull_painting_bulk_carrier_panamax"))
	set_initial_technology_share("*", "lighting_system_bulk_carrier_panamax", Curve("uptake_lighting_system_bulk_carrier_panamax"))
	set_initial_technology_share("*", "propeller_improvement_devices_bulk_carrier_panamax", Curve("uptake_propeller_improvement_devices_bulk_carrier_panamax"))
	set_initial_technology_share("*", "variable_frequency_drive_bulk_carrier_panamax", Curve("uptake_variable_frequency_drive_bulk_carrier_panamax"))

	# fuel conversions
	set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 17.5e6)
	set_fuel_conversion_cost("*ice_oil*", "*ice_ammonia*", 24.1e6)
	set_fuel_conversion_cost("*ice_methane*", "*ice_ammonia*", 14.2e6)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.7
}
