# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_tanker_47k_dwt" {
	RouteType = REGIONAL_TRIP

	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [41, 7]
	
	TimeAtSea = 0.46
	ConditionDistribution = [0.01, 0.02, 0.05, 0.14, 0.20, 0.07, 0.01, 0.01, 0.02, 0.05, 0.14, 0.20, 0.07, 0.01]
	Speeds = [8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5]
	CapacityUtilizations = [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
}
