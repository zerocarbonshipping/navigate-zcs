# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "ferry" {

	# vessel types
	Vessels = [
		Vessel("ferry_ice_methane"),
		Vessel("ferry_ice_methanol"),
		Vessel("ferry_ice_oil")
	]

	# initial conditions
	InitialVessels = Variable("initial_vessels_ferry")

	InitialSplit = [
		0.047,
		0.001,
		0.951
	]

	InitialAgeDistribution = [
		Curve("age_dist_ferry_methane"),
		Curve("age_dist_ferry_methanol"),
		Curve("age_dist_ferry_oil")
	]


	# trade growth
	TradeGrowth = Forecast("trade_growth_ferry")

	# orderbook
	Orderbooks = [
		Forecast("orderbook_ferry_methane"),
		Forecast("orderbook_ferry_methanol"),
		Forecast("orderbook_ferry_oil")
	]

	# speed management
	AllowSpeedManagement = FALSE
}
