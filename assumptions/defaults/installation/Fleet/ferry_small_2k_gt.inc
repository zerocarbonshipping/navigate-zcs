# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry, owner to confirm (Ship Design & Technology).

Fleet "ferry_small_2k_gt" {

	# vessel types
	Vessels = [
		Vessel("ferry_small_2k_gt_ice_methane"),
		Vessel("ferry_small_2k_gt_ice_methanol"),
		Vessel("ferry_small_2k_gt_ice_oil")
	]

	# initial conditions: initial vessels from the Assumptions record
	# vessels/new_segments_fleet_counts; the initial split is inherited from the parent, not
	# sourced; no public age distribution or orderbook exists for this segment, so none is set
	# (0) pending the fleet pipeline, see worklogs/vessels/new_segments/status.md
	InitialVessels = Variable("initial_vessels_ferry_small_2k_gt")

	InitialSplit = [
		0.047,
		0.001,
		0.951
	]

	InitialAgeDistribution = [
		0,
		0,
		0
	]

	# trade growth
	TradeGrowth = Forecast("trade_growth_ferry_small_2k_gt")

	# orderbook
	Orderbooks = [
		0,
		0,
		0
	]

	# speed management
	AllowSpeedManagement = FALSE
}
