# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_general_cargo" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [16, 4]
	
	TimeAtSea = 0.548
	ConditionDistribution = [1]
	Speeds =                [11.2]
	CapacityUtilizations = 	[0.5]
}
