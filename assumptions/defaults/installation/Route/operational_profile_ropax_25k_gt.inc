# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# inherited from ferry, pending the fleet pipeline (Fleet Performance & EE steer);
# not sourced for this segment.

Route "operational_profile_ropax_25k_gt" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [40, 10]
	
	TimeAtSea = 0.5
	ConditionDistribution = [1]
	Speeds =                [14]
	CapacityUtilizations =  [0.75]
}
