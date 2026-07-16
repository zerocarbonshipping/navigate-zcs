# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_tanker_127k_dwt" {
	RouteType = REGIONAL_TRIP

	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [30, 5]
	
	TimeAtSea = 0.51
	ConditionDistribution = [0.01, 0.02, 0.04, 0.08, 0.19, 0.21, 0.05, 0.01, 0.01, 0.03, 0.05, 0.13, 0.14, 0.03]
	Speeds = [7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5]
	CapacityUtilizations = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]
}
