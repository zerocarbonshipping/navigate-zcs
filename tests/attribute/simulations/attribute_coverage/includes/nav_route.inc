# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Routes and Ports
#
# Attributes covered:
#   Route: RouteType, Ports, TimeAtSea, PortDurations, PortCalls,
#          Distances, ConditionDistribution, Speeds, CapacityUtilizations
#   Port:  ShorePowerCost, ShorePowerConnectionShare
#
# Commands covered:
#   Route: set_voyage_distribution
#   Port:  set_bunkering_allowed, set_bunkering_limit, set_bunkering_inertia,
#          set_handling_cost, set_bunker_price_overwrite, set_bunker_wtt_overwrite,
#          set_shore_power_emission_factor

# Two ports for ROUND_TRIP legs
Port "port_a" {
	ShorePowerCost = 50
	ShorePowerConnectionShare = 0.1
	set_handling_cost("hfo", 20)
	set_bunker_price_overwrite("hfo", 600)
	set_bunker_price_overwrite("lng", 800)
	set_bunker_price_overwrite("bio_methanol", 1200)
	set_bunker_price_overwrite("blue_ammonia", 1000)
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
}

# REGIONAL_TRIP covers: TimeAtSea, PortCalls, ConditionDistribution
Route "route_regional" {
	RouteType = REGIONAL_TRIP
	Ports = Port("port_a")
	TimeAtSea = 0.75
	PortCalls = [100]
	ConditionDistribution = [1.0]
	Speeds = [10]
	CapacityUtilizations = [0.7]
}

# ROUND_TRIP covers: Distances, PortDurations, set_voyage_distribution
Route "route_roundtrip" {
	RouteType = ROUND_TRIP
	Ports = [Port("port_a"), Port("port_b")]
	Distances = [1000, 1000]
	PortDurations = [2, 2]
	Speeds = [12, 12]
	CapacityUtilizations = [0.8, 0.5]
	set_voyage_distribution("port_a", "port_b", 0.5)
	set_voyage_distribution("port_b", "port_a", 0.5)
}
