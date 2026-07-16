# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "container_1500_teu_ice_oil" {
	
	PropulsionLoad = Curve("container_1500_teu_propulsion_load")
	ElectricalLoadAtSea = Variable("container_1500_teu_electrical_load_sea")
	ElectricalLoadInPort = Variable("container_1500_teu_electrical_load_port")
	HeatLoadAtSea = Variable("container_1500_teu_heat_load_sea")
	HeatLoadInPort = Variable("container_1500_teu_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_container_1500_teu")
	Tanks = [Tank("main_oil_container_1500_teu")]
	
	Route = Route("operational_profile_container_1500_teu")
	NominalCapacity = Variable("container_1500_teu_nominal_capacity")
	Lifetime = Variable("container_1500_teu_lifetime")
	
	CAPEX = Forecast("container_1500_teu_capex")
	OPEX = Forecast("container_1500_teu_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
