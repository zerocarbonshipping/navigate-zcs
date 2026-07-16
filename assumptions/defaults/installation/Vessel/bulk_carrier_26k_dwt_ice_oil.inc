# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "bulk_carrier_26k_dwt_ice_oil" {
	
	PropulsionLoad = Surface("bulk_carrier_26k_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("bulk_carrier_26k_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("bulk_carrier_26k_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("bulk_carrier_26k_dwt_heat_load_sea")
	HeatLoadInPort = Variable("bulk_carrier_26k_dwt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_bulk_carrier_26k_dwt")
	Tanks = [Tank("main_oil_bulk_carrier_26k_dwt")]
	
	Route = Route("operational_profile_bulk_carrier_26k_dwt")
	NominalCapacity = Variable("bulk_carrier_26k_dwt_nominal_capacity")
	Lifetime = Variable("bulk_carrier_26k_dwt_lifetime")
	
	CAPEX = Forecast("bulk_carrier_26k_dwt_capex")
	OPEX = Forecast("bulk_carrier_26k_dwt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
