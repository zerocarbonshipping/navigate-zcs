# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A two-port REGIONAL_TRIP route for both vessels of the base fleet. Reads the
# speed distribution, TimeAtSea and the per-port PortCalls.
Route "combination_route" {
	RouteType = REGIONAL_TRIP
	Ports = [Port("port_global"), Port("port_europe")]
	PortCalls = [41, 7]
	TimeAtSea = 0.63
	ConditionDistribution = [0.2, 0.6, 0.2]
	Speeds = [12.0, 16.0, 20.0]         # knots
	CapacityUtilizations = [0.7, 0.7, 0.7]
}

Vessel "container_15000_teu_ice_*" {
	Route = Route("combination_route")
}
