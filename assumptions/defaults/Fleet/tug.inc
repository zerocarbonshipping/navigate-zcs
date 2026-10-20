# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "tug" {	
	
	# vessel types
	Vessels = [
		Vessel("tug_ice_ammonia"),
		Vessel("tug_ice_methane"),
		Vessel("tug_ice_methanol"),
		Vessel("tug_ice_oil")
	]

	# initial conditions
	InitialVessels = Variable("initial_vessels_tug")

	InitialSplit = [
		0.000,
		0.001,
		0.000,
		0.999
	]

	InitialAgeDistribution = [
		0,
		Curve("age_dist_tug_methane"),
		0,
		Curve("age_dist_tug_oil")
	]


	# trade growth
	TradeGrowth = Forecast("trade_growth_tug")

	Orderbooks = [
		Forecast("orderbook_tug_ammonia"),
		Forecast("orderbook_tug_methane"),
		Forecast("orderbook_tug_methanol"),
		Forecast("orderbook_tug_oil")
	]

	# this is an additional file required to disable tug when including domestic shipping. Since there is no international tug it will throw an error in international only to attempt to wildcard tug fleet.
	# speed management
	AllowSpeedManagement = FALSE
}
