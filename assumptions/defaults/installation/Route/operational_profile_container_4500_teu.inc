# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_container_4500_teu" {
	RouteType = REGIONAL_TRIP

	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [62, 10]
	
	TimeAtSea = 0.64
	ConditionDistribution = [0.01, 0.02, 0.05, 0.09, 0.12, 0.13, 0.13, 0.12, 0.13, 0.11, 0.06, 0.02, 0.01]
	Speeds = [8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5]
	CapacityUtilizations = [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7]
}
