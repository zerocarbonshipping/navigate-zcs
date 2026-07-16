# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "operational_profile_roro_4000_ceu" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [100, 25]
	
	TimeAtSea = 0.616
	ConditionDistribution = [1]
	Speeds =                [15.8]
	CapacityUtilizations =  [0.75]
}
