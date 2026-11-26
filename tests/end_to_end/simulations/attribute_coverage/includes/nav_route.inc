# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Routes and Ports
#
# Attributes covered:
#   Route: RouteType, Ports, TimeAtSea
#   Port:  ShorePowerPrice, ShorePowerAvailability
#
# Commands covered:
#   Route: set_speed, set_utilization, set_distance, set_port_duration,
#          set_distance_share, set_port_calls
#   Port:  set_allow_bunkering, set_bunkering_limit, set_bunkering_inertia,
#          set_handling_cost, set_fuel_price, set_fuel_wtt,
#          set_shore_power_wtt

# Two ports for the legs of both route types
Port "port_a" {
	ShorePowerPrice = 50
	ShorePowerAvailability = 0.1
	set_bunkering_limit("lng", INF)
	set_handling_cost("hfo", 20)
	set_fuel_price("hfo", 600)
	set_fuel_price("lng", 800)
	set_fuel_price("bio_methanol", 1200)
	set_fuel_price("blue_ammonia", 1000)
	set_fuel_price("ethanol", 900)
	set_fuel_price("hydrogen", 3000)
	set_fuel_price("lpg", 700)
	set_fuel_price("electricity", 250)
	set_fuel_wtt("hfo", "carbon_dioxide", 0.62)
	set_shore_power_wtt("carbon_dioxide", 0.180)
}

Port "port_b" {
	ShorePowerPrice = 60
	ShorePowerAvailability = 0.2
	set_fuel_price("hfo", 550)
	set_fuel_price("lng", 850)
	set_fuel_price("bio_methanol", 1250)
	set_fuel_price("blue_ammonia", 1050)
	set_fuel_price("ethanol", 950)
	set_fuel_price("hydrogen", 3100)
	set_fuel_price("lpg", 720)
	set_fuel_price("electricity", 260)
}

# TRAMP covers: TimeAtSea, set_distance_share, set_port_calls, and a
# speed Curve with a utilization Curve over the same speeds
Route "route_tramp" {
	RouteType = TRAMP
	Ports = [Port("port_a"), Port("port_b")]
	TimeAtSea = 0.75
	set_port_calls("port_a", 100)
	set_port_calls("port_b", 20)
	set_distance_share("*", "*", 0.2)
	set_distance_share("port_a", "port_a", 0.4)
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
