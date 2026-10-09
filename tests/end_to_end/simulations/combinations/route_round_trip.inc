# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A two-port ROUND_TRIP route for both vessels of the base fleet. Reads the
# per-leg Speeds and Distances and the per-port PortDurations.
Route "combination_route" {
	RouteType = ROUND_TRIP
	Ports = [Port("port_global"), Port("port_europe")]
	Speeds = [16.0, 16.0]               # knots
	Distances = [11000, 11000]          # nautical miles
	PortDurations = [2.0, 2.0]          # days
	CapacityUtilizations = [0.7, 0.7]
}

Vessel "container_15000_teu_ice_*" {
	Route = Route("combination_route")
}
