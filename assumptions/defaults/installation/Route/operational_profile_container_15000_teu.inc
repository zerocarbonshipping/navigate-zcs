# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_container_15000_teu" {
	# The route type is an internal calculation choice and does not describe how
	# the segment operates.
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 41)
	set_port_calls("port_europe", 7)

	TimeAtSea = 0.63
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", Curve("speed_distribution_container_15000_teu"))
	set_utilization("*", "*", 0.7)
}
