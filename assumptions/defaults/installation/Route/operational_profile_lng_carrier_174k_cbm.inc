# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# inherited from gas_carrier_100k_cbm, pending the fleet pipeline (Fleet Performance & EE steer);
# not sourced for this segment.

Route "operational_profile_lng_carrier_174k_cbm" {
	RouteType = REGIONAL_TRIP
	
	Ports = [Port("port_global"), Port("port_europe")]
    PortCalls = [24, 6]
	
	TimeAtSea = 0.684
	ConditionDistribution = [1]
	Speeds = 				[16.6]
	CapacityUtilizations = 	[0.5]
}
