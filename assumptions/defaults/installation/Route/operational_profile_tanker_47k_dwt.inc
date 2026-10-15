# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_tanker_47k_dwt" {
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 41)
	set_port_calls("port_europe", 7)

	TimeAtSea = 0.46
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", Curve("speed_distribution_tanker_47k_dwt"))
	set_utilization("*", "*", 0.5)
}
