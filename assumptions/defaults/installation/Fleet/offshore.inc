# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "offshore" {

	# vessel types
	Vessels = [
		Vessel("offshore_ice_ammonia"),
		Vessel("offshore_ice_methane"),
		Vessel("offshore_ice_methanol"),
		Vessel("offshore_ice_oil")
	]

	# initial conditions
	InitialVessels = Variable("initial_vessels_offshore")

	InitialSplit = [
		0.000,
		0.005,
		0.000,
		0.995
	]

	InitialAgeDistribution = [
		0,
		Curve("age_dist_offshore_methane"),
		0,
		Curve("age_dist_offshore_oil")
	]


	# trade growth
	TradeGrowth = Forecast("trade_growth_offshore")

	# orderbooks
	Orderbooks = [
		Forecast("orderbook_offshore_ammonia"),
		Forecast("orderbook_offshore_methane"),
		Forecast("orderbook_offshore_methanol"),
		Forecast("orderbook_offshore_oil")
	]

	# speed management
	AllowSpeedManagement = FALSE
}
