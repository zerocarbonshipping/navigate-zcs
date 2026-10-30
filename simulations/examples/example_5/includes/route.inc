# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ROUTES - three Caribbean ports and Miami.
#
# Each Caribbean port stands for a group of islands:
#   jamaica     Kingston, the Greater Antilles transhipment hub
#   trinidad    Port of Spain and Point Lisas, with Tobago
#   martinique  Fort-de-France, for the French Antilles (an EU outermost region)
#
# Distances: great-circle between the ports, plus 10 % for the sea route
# (INVENTED factor; the research found no citable sea-distance table and puts
# real routes 5-15 % above great-circle). Miami - Kingston is INVENTED at 700 nm,
# since the great circle (505 nm) crosses Cuba.
#
# Speeds, time at sea and capacity use come from each class's operational
# profile in the library, unless marked otherwise.

Vessel "reg_tug_*"    { Route = Route("reg_tug_route") }
Vessel "reg_ferry_*"  { Route = Route("reg_ferry_route") }
Vessel "reg_cargo_*"  { Route = Route("reg_cargo_route") }
Vessel "reg_tanker_*" { Route = Route("reg_tanker_route") }
Vessel "intl_feeder_*" { Route = Route("intl_feeder_route") }

# ---- tugs work inside their port --------------------------------------------
# INVENTED: tugs spread over the three ports by 2025 container throughput
# (Kingston 2.66 M TEU, Port of Spain + Point Lisas 0.57 M, Fort-de-France
# 0.19 M; R.J. Sánchez, PortEconomics, 2 Oct 2026), as a proxy for harbour work.
Route "reg_tug_route" {
	RouteType = REGIONAL_TRIP
	Ports = [Port("jamaica"), Port("trinidad"), Port("martinique")]
	PortCalls = [39, 8.5, 2.5]   # the library's 50 calls a year, split as above
	TimeAtSea = 0.22
	ConditionDistribution = [1]
	Speeds = [10.7]
	CapacityUtilizations = [0.8]
	set_voyage_distribution("jamaica", "jamaica", 0.78)
	set_voyage_distribution("trinidad", "trinidad", 0.17)
	set_voyage_distribution("martinique", "martinique", 0.05)
}

# ---- ferries: Trinidad - Tobago, and around the French Antilles --------------
# INVENTED: half the ferry work in each group; none in Jamaica.
Route "reg_ferry_route" {
	RouteType = REGIONAL_TRIP
	Ports = [Port("trinidad"), Port("martinique")]
	PortCalls = [25, 25]
	TimeAtSea = 0.5
	ConditionDistribution = [1]
	Speeds = [14]
	CapacityUtilizations = [0.75]
	set_voyage_distribution("trinidad", "trinidad", 0.5)
	set_voyage_distribution("martinique", "martinique", 0.5)
}

# ---- regional cargo and tankers: a loop out of Trinidad ----------------------
# Great-circle legs: Point Lisas - Fort-de-France 253 nm, Fort-de-France -
# Kingston 928 nm, Kingston - Point Lisas 1,000 nm.
Route "reg_cargo_route" {
	RouteType = ROUND_TRIP
	Ports = [Port("trinidad"), Port("martinique"), Port("jamaica")]
	Distances = [278, 1021, 1100]
	Speeds = [11.2, 11.2, 11.2]
	CapacityUtilizations = [0.5, 0.5, 0.5]
	# library time at sea 0.548: 8.9 days sailing per loop, 7.4 days in port
	PortDurations = [2.45, 2.45, 2.45]
}

Route "reg_tanker_route" {
	RouteType = ROUND_TRIP
	Ports = [Port("trinidad"), Port("martinique"), Port("jamaica")]
	Distances = [278, 1021, 1100]
	# INVENTED: 10.5 knots, the middle of the library's 6.5-14.5 range
	Speeds = [10.5, 10.5, 10.5]
	# INVENTED: loaded at Trinidad's terminals, half discharged at each call
	CapacityUtilizations = [1.0, 0.5, 0.0]
	# library time at sea 0.3: 9.5 days sailing per loop, 22.2 days in port
	PortDurations = [7.4, 7.4, 7.4]
}

# ---- international feeders: Miami and the three Caribbean ports --------------
# Great-circle: Fort-de-France - Miami 1,266 nm.
Route "intl_feeder_route" {
	RouteType = ROUND_TRIP
	Ports = [Port("miami"), Port("jamaica"), Port("trinidad"), Port("martinique")]
	Distances = [700, 1100, 278, 1393]
	# INVENTED: 13 knots, the middle of the library's 7.5-18.5 range
	Speeds = [13, 13, 13, 13]
	CapacityUtilizations = [0.7, 0.7, 0.7, 0.7]
	# library: 72 calls a year at time at sea 0.5, so 2.5 days per call
	PortDurations = [2.5, 2.5, 2.5, 2.5]
}
