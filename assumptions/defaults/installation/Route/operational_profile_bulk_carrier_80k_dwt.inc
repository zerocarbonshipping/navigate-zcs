# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_bulk_carrier_80k_dwt" {
	RouteType = REGIONAL_TRIP

	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [21, 3]
	
	TimeAtSea = 0.55
	ConditionDistribution = [0.03, 0.1, 0.14, 0.1, 0.02, 0.01, 0.04, 0.15, 0.23, 0.14, 0.04]
	Speeds = [9.5, 10.5, 11.5, 12.5, 13.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5]
	CapacityUtilizations = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1]
}
