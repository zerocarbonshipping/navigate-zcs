# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_tanker_127k_dwt" {
	RouteType = TRAMP

	Ports = [Port("port_global"), Port("port_europe")]
	set_port_calls("port_global", 30)
	set_port_calls("port_europe", 5)

	TimeAtSea = 0.51
	set_voyage_distribution("*", "*", 1)

	set_speed("*", "*", Curve("speed_distribution_tanker_127k_dwt"))
	set_utilization("*", "*", Curve("utilization_tanker_127k_dwt"))
}
