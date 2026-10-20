# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "other" {

	# vessel types
	Vessels = [
		Vessel("other_ice_ammonia"),
		Vessel("other_ice_methane"),
		Vessel("other_ice_methanol"),
		Vessel("other_ice_oil")
	]
	
	# initial conditions
	InitialVessels = Variable("initial_vessels_other")
	
	InitialSplit = [
		0.000,
		0.020,
		0.000,
		0.980
	]
	
	InitialAgeDistribution = [
		0,
		Curve("age_dist_other_methane"),
		0,
		Curve("age_dist_other_oil")
	]
	

	# trade growth
	TradeGrowth = Forecast("trade_growth_other")
	
	# orderbooks
	Orderbooks = [
		Forecast("orderbook_other_ammonia"),
		Forecast("orderbook_other_methane"),
		Forecast("orderbook_other_methanol"),
		Forecast("orderbook_other_oil")
	]

	# speed management
	AllowSpeedManagement = FALSE
}
