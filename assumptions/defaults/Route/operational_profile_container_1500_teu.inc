# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_container_1500_teu" {
	# The route type is an internal calculation choice and does not describe how
	# the segment operates.
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 62)
	set_port_calls("port_europe", 10)

	TimeAtSea = 0.50
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", Curve("speed_distribution_container_1500_teu"))
	set_utilization("*", "*", 0.7)
}
