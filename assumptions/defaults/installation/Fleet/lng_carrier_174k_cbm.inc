# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm, owner to confirm (Ship Design & Technology).

Fleet "lng_carrier_174k_cbm" {

	# vessel types
	Vessels = [
		Vessel("lng_carrier_174k_cbm_ice_ammonia"),
		Vessel("lng_carrier_174k_cbm_ice_methane"),
		Vessel("lng_carrier_174k_cbm_ice_methanol"),
		Vessel("lng_carrier_174k_cbm_ice_oil")
	]
	
	# initial conditions: initial vessels, split, age distribution and orderbook from the
	# Assumptions records vessels/new_segments_fleet_counts and
	# vessels/lng_carrier_174k_cbm_fleet_age_distribution; no age distribution is set for the
	# oil-fuelled (slow-speed diesel) ships
	InitialVessels = Variable("initial_vessels_lng_carrier_174k_cbm")
	
	InitialSplit = [
		0,
		0.93,
		0,
		0.07
	]
	
	InitialAgeDistribution = [
		0,
		Curve("age_dist_lng_carrier_174k_cbm_methane"),
		0,
		0
	]
	
	
	# trade growth
	TradeGrowth = Forecast("trade_growth_gas_carrier")
	
	# orderbooks
	Orderbooks = [
		0,
		Forecast("orderbook_lng_carrier_174k_cbm_methane"),
		0,
		0
	]

	# technologies: none inherited, the parent's are segment-specific nodes; pending
	# the EE applicability matrix for the new segments (Fleet Performance & EE)

	# speed management
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.6
}
