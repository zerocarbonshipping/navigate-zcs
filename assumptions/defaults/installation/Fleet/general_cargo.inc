# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "general_cargo" {

	# vessel types
	Vessels = [
		Vessel("general_cargo_ice_ammonia"),
		Vessel("general_cargo_ice_methane"),
		Vessel("general_cargo_ice_methanol"),
		Vessel("general_cargo_ice_oil")
	]

	# initial conditions
	InitialVessels = Variable("initial_vessels_general_cargo")

	InitialSplit = [
		0.000,
		0.002,
		0.000,
		0.998
	]

	InitialAgeDistribution = [
		0,
		Curve("age_dist_general_cargo_methane"),
		0,
		Curve("age_dist_general_cargo_oil")
	]


	# trade growth
	TradeGrowth = Forecast("trade_growth_general_cargo")

	# orderbooks
	Orderbooks = [
		Forecast("orderbook_general_cargo_ammonia"),
		Forecast("orderbook_general_cargo_methane"),
		Forecast("orderbook_general_cargo_methanol"),
		Forecast("orderbook_general_cargo_oil")
	]

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.4
}
