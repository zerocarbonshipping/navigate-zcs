# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fleet "cruise_175k_gt" {

	# vessel types
	Vessels = [
		Vessel("cruise_175k_gt_ice_methane"),
		Vessel("cruise_175k_gt_ice_methanol"),
		Vessel("cruise_175k_gt_ice_oil")
	]
	
	# initial conditions
	InitialVessels = Variable("initial_vessels_cruise_175k_gt")
	
	InitialSplit = [
		0.272,
		0.000,
		0.728
	]
	
	InitialAgeDistribution = [
		Curve("age_dist_cruise_175k_gt_methane"),
		0,
		Curve("age_dist_cruise_175k_gt_oil")
	]
	

	# trade growth
	TradeGrowth = Forecast("trade_growth_cruise")
	
	# orderbook
	Orderbooks = [
		Forecast("orderbook_cruise_175k_gt_methane"),
		Forecast("orderbook_cruise_175k_gt_methanol"),
		Forecast("orderbook_cruise_175k_gt_oil")
	]

    # speed management
    AllowSpeedManagement = FALSE
}
