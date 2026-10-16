# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A two-port LINER route for both vessels of the base fleet. Reads each leg's
# speed, distance, port duration and utilization.
Route "combination_route" {
	RouteType = LINER
	Ports = [Port("port_global"), Port("port_europe")]

	set_speed("*", "*", 16.0)           # knots
	set_distance("*", "*", 11000)       # nautical miles
	set_port_duration("*", "*", 2.0)    # days
	set_utilization("*", "*", 0.7)
}

Vessel "container_15000_teu_ice_*" {
	Route = Route("combination_route")
}
