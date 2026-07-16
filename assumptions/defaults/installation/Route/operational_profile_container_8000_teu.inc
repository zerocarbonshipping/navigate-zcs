# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_container_8000_teu" {
	RouteType = REGIONAL_TRIP

	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [52, 8]
	
	TimeAtSea = 0.66
	ConditionDistribution = [0.01, 0.01, 0.03, 0.05, 0.08, 0.09, 0.1, 0.12, 0.14, 0.14, 0.13, 0.07, 0.02, 0.01]
	Speeds = [8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5]
	CapacityUtilizations = [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
}
