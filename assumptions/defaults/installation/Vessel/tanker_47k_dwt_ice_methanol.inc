# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "tanker_47k_dwt_ice_methanol" {
	
	PropulsionLoad = Surface("tanker_47k_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("tanker_47k_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("tanker_47k_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("tanker_47k_dwt_heat_load_sea")
	HeatLoadInPort = Variable("tanker_47k_dwt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methanol_tanker_47k_dwt")
	Tanks = [Tank("main_methanol_tanker_47k_dwt"), Tank("pilot_oil_tanker_47k_dwt")]
	
	Route = Route("operational_profile_tanker_47k_dwt")
	NominalCapacity = Variable("tanker_47k_dwt_nominal_capacity")
	Lifetime = Variable("tanker_47k_dwt_lifetime")
	
	CAPEX = Forecast("tanker_47k_dwt_capex")
	OPEX = Forecast("tanker_47k_dwt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
