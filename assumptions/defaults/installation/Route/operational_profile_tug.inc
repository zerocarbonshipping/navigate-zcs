# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_tug" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [40, 10]
	
	TimeAtSea = 0.22
	ConditionDistribution = [1]
	Speeds =                [10.7]
	CapacityUtilizations =  [0.8]
}
