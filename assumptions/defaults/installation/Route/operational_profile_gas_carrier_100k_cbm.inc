# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_gas_carrier_100k_cbm" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [24, 6]
	
	TimeAtSea = 0.684
	ConditionDistribution = [1]
	Speeds = 				[16.6]
	CapacityUtilizations = 	[0.5]
}
