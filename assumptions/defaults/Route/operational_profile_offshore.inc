# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_offshore" {
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 8)
	set_port_calls("port_europe", 2)

	TimeAtSea = 0.22
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", 10)
	set_utilization("*", "*", 0.5)
}
