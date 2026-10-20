# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Routes and Ports
#
# Attributes covered:
#   Route: RouteType, Ports, TimeAtSea
#   Port:  ShorePowerCost, ShorePowerConnectionShare
#
# Commands covered:
#   Route: set_speed, set_utilization, set_distance, set_port_duration,
#          set_voyage_distribution, set_port_calls
#   Port:  set_bunkering_allowed, set_bunkering_limit, set_bunkering_inertia,
#          set_handling_cost, set_bunker_price_overwrite, set_bunker_wtt_overwrite,
#          set_shore_power_emission_factor

# Two ports for the legs of both route types
Port "port_a" {
	ShorePowerCost = 50
	ShorePowerConnectionShare = 0.1
	set_bunkering_limit("lng", INF)
	set_handling_cost("hfo", 20)
	set_bunker_price_overwrite("hfo", 600)
	set_bunker_price_overwrite("lng", 800)
	set_bunker_price_overwrite("bio_methanol", 1200)
	set_bunker_price_overwrite("blue_ammonia", 1000)
	set_bunker_price_overwrite("ethanol", 900)
	set_bunker_price_overwrite("hydrogen", 3000)
	set_bunker_price_overwrite("lpg", 700)
	set_bunker_price_overwrite("electricity", 250)
	set_bunker_wtt_overwrite("hfo", "carbon_dioxide", 0.62)
	set_shore_power_emission_factor("carbon_dioxide", 0.180)
}

Port "port_b" {
	ShorePowerCost = 60
	ShorePowerConnectionShare = 0.2
	set_bunker_price_overwrite("hfo", 550)
	set_bunker_price_overwrite("lng", 850)
	set_bunker_price_overwrite("bio_methanol", 1250)
	set_bunker_price_overwrite("blue_ammonia", 1050)
	set_bunker_price_overwrite("ethanol", 950)
	set_bunker_price_overwrite("hydrogen", 3100)
	set_bunker_price_overwrite("lpg", 720)
	set_bunker_price_overwrite("electricity", 260)
}

# TRAMP covers: TimeAtSea, set_voyage_distribution, set_port_calls, and a
# speed Curve with a utilization Curve over the same speeds
Route "route_tramp" {
	RouteType = TRAMP
	Ports = [Port("port_a"), Port("port_b")]
	TimeAtSea = 0.75
	set_port_calls("port_a", 100)
	set_port_calls("port_b", 20)
	set_voyage_distribution("*", "*", 0.2)
	set_voyage_distribution("port_a", "port_a", 0.4)
	set_speed("*", "*", Curve("curve_tramp_speed"))
	set_utilization("*", "*", Curve("curve_tramp_utilization"))
	set_utilization("port_b", "port_b", 0.7)
}

# LINER covers: set_distance, set_port_duration, and one speed per leg
Route "route_liner" {
	RouteType = LINER
	Ports = [Port("port_a"), Port("port_b")]
	set_distance("*", "*", 1000)
	set_port_duration("*", "*", 2)
	set_speed("*", "*", 12)
	set_utilization("port_a", "port_b", 0.8)
	set_utilization("port_b", "port_a", 0.5)
}

# Share of the time at sea sailed at each speed
Curve "curve_tramp_speed" {
	Table = [
		9,	0.3;
		11,	0.7;
	]
}

# Cargo capacity utilization at each speed: ballast at 9 knots, laden at 11
Curve "curve_tramp_utilization" {
	Table = [
		9,	0;
		11,	1;
	]
}
