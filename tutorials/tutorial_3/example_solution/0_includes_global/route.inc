# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of route 

Route "route" {
	RouteType = REGIONAL_TRIP 		
	Ports = [Port("port")]
	TimeAtSea = 0.75		
	ConditionDistribution = [1.0] 
	Speeds = [10]
}
