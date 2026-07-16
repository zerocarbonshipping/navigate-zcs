# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_offshore" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [8, 2]

	TimeAtSea = 0.22
	ConditionDistribution = [1]
	Speeds = 				[10]
	CapacityUtilizations = 	[0.5]
}
