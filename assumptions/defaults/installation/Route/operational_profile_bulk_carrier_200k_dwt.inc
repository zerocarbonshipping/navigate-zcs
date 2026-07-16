# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_bulk_carrier_200k_dwt" {
	RouteType = REGIONAL_TRIP

	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [17, 3]
	
	TimeAtSea = 0.65
	ConditionDistribution = [0.01, 0.06, 0.16, 0.14, 0.09, 0.03, 0.01, 0.01, 0.06, 0.16, 0.14, 0.09, 0.03, 0.01]
	Speeds = [8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5]
	CapacityUtilizations = [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
}
