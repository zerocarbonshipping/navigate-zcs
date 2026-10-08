# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm, owner to confirm (Ship Design & Technology).

Fleet "lpg_carrier_84k_cbm" {

	# vessel types
	Vessels = [
		Vessel("lpg_carrier_84k_cbm_ice_ammonia"),
		Vessel("lpg_carrier_84k_cbm_ice_methane"),
		Vessel("lpg_carrier_84k_cbm_ice_methanol"),
		Vessel("lpg_carrier_84k_cbm_ice_oil")
	]
	
	# initial conditions: initial vessels from the Assumptions record
	# vessels/new_segments_fleet_counts; the initial split is inherited from the parent, not
	# sourced; no public age distribution or orderbook exists for this segment, so none is set
	# (0) pending the fleet pipeline, see worklogs/vessels/new_segments/status.md
	InitialVessels = Variable("initial_vessels_lpg_carrier_84k_cbm")
	
	InitialSplit = [
		0.000,
		0.655,
		0.000,
		0.345
	]
	
	InitialAgeDistribution = [
		0,
		0,
		0,
		0
	]
	
	
	# trade growth
	TradeGrowth = Forecast("trade_growth_gas_carrier")
	
	# orderbooks
	Orderbooks = [
		0,
		0,
		0,
		0
	]

	# technologies: none inherited, the parent's are segment-specific nodes; pending
	# the EE applicability matrix for the new segments (Fleet Performance & EE)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.6
}
