# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_cruise_175k_gt" {
	# The route type is an internal calculation choice and does not describe how
	# the segment operates.
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 168)
	set_port_calls("port_europe", 42)

	TimeAtSea = 0.6
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", Curve("speed_distribution_cruise_175k_gt"))
	set_utilization("*", "*", 0.8)
}
