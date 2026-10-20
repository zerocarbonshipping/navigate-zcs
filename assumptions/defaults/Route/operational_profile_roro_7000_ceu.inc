# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_roro_7000_ceu" {
	# The route type is an internal calculation choice and does not describe how
	# the segment operates.
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 100)
	set_port_calls("port_europe", 25)

	TimeAtSea = 0.876
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", 15.5)
	set_utilization("*", "*", 0.75)
}
