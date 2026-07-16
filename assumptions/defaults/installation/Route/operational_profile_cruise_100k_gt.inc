# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_cruise_100k_gt" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [168, 42]
	
	TimeAtSea = 0.6
	ConditionDistribution = [0.05, 0.09, 0.18, 0.09, 0.14, 0.09, 0.27, 0.09]
	Speeds = 				[  10,   12,   14,   15,   16,   17,   18,   21]
	CapacityUtilizations = 	[ 0.8,  0.8,  0.8,  0.8,  0.8,  0.8,  0.8,  0.8]
}
