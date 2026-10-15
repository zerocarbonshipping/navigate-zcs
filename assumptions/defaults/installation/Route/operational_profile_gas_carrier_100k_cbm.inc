# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_gas_carrier_100k_cbm" {
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 24)
	set_port_calls("port_europe", 6)

	TimeAtSea = 0.684
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", 16.6)
	set_utilization("*", "*", 0.5)
}
