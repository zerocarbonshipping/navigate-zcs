# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_other" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [1, 1]
	
	TimeAtSea = 0.5
	ConditionDistribution = [1]
	Speeds =                [14.9]
	CapacityUtilizations = 	[0.5]
}
