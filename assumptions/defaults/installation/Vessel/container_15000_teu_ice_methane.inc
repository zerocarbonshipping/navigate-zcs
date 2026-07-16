# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "container_15000_teu_ice_methane" {
	
	PropulsionLoad = Curve("container_15000_teu_propulsion_load")
	ElectricalLoadAtSea = Variable("container_15000_teu_electrical_load_sea")
	ElectricalLoadInPort = Variable("container_15000_teu_electrical_load_port")
	HeatLoadAtSea = Variable("container_15000_teu_heat_load_sea")
	HeatLoadInPort = Variable("container_15000_teu_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methane_container_15000_teu")
	Tanks = [Tank("main_methane_container_15000_teu"), Tank("pilot_oil_container_15000_teu")]
	
	Route = Route("operational_profile_container_15000_teu")
	NominalCapacity = Variable("container_15000_teu_nominal_capacity")
	Lifetime = Variable("container_15000_teu_lifetime")
	
	CAPEX = Forecast("container_15000_teu_capex")
	OPEX = Forecast("container_15000_teu_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
