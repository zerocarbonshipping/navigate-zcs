# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_tug" {
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 40)
	set_port_calls("port_europe", 10)

	TimeAtSea = 0.22
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", 10.7)
	set_utilization("*", "*", 0.8)
}
