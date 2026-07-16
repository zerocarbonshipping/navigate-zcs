# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "tanker_7500_dwt_ice_oil" {
	
	PropulsionLoad = Surface("tanker_7500_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("tanker_7500_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("tanker_7500_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("tanker_7500_dwt_heat_load_sea")
	HeatLoadInPort = Variable("tanker_7500_dwt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_tanker_7500_dwt")
	Tanks = [Tank("main_oil_tanker_7500_dwt")]
	
	Route = Route("operational_profile_tanker_7500_dwt")
	NominalCapacity = Variable("tanker_7500_dwt_nominal_capacity")
	Lifetime = Variable("tanker_7500_dwt_lifetime")
	
	CAPEX = Forecast("tanker_7500_dwt_capex")
	OPEX = Forecast("tanker_7500_dwt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
