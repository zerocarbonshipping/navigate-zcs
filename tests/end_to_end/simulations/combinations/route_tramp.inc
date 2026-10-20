# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A two-port TRAMP route for both vessels of the base fleet. Reads TimeAtSea,
# the port calls, the voyage distribution and a speed distribution per leg.
Curve "combination_route_speeds" {
	Table = [
		12.0,  0.2;                       # knots, share of the leg's time at sea
		16.0,  0.6;
		20.0,  0.2;
	]
}

Route "combination_route" {
	RouteType = TRAMP
	Ports = [Port("port_global"), Port("port_europe")]
	TimeAtSea = 0.63

	set_port_calls("port_global", 41)
	set_port_calls("port_europe", 7)

	set_voyage_distribution("*", "*", 1)
	set_speed("*", "*", Curve("combination_route_speeds"))
	set_utilization("*", "*", 0.7)
}

Vessel "container_15000_teu_ice_*" {
	Route = Route("combination_route")
}
