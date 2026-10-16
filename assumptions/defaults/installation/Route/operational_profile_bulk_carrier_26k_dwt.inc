# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_bulk_carrier_26k_dwt" {
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 31)
	set_port_calls("port_europe", 5)

	TimeAtSea = 0.41
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", Curve("speed_distribution_bulk_carrier_26k_dwt"))
	set_utilization("*", "*", 0.5)
}
