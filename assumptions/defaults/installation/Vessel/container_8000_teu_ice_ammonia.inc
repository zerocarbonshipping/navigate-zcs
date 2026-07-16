# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "container_8000_teu_ice_ammonia" {
	
	PropulsionLoad = Curve("container_8000_teu_propulsion_load")
	ElectricalLoadAtSea = Variable("container_8000_teu_electrical_load_sea")
	ElectricalLoadInPort = Variable("container_8000_teu_electrical_load_port")
	HeatLoadAtSea = Variable("container_8000_teu_heat_load_sea")
	HeatLoadInPort = Variable("container_8000_teu_heat_load_port")
	
	PowerSystem = PowerSystem("ice_ammonia_container_8000_teu")
	Tanks = [Tank("main_ammonia_container_8000_teu"), Tank("pilot_oil_container_8000_teu")]
	
	Route = Route("operational_profile_container_8000_teu")
	NominalCapacity = Variable("container_8000_teu_nominal_capacity")
	Lifetime = Variable("container_8000_teu_lifetime")
	
	CAPEX = Forecast("container_8000_teu_capex")
	OPEX = Forecast("container_8000_teu_opex")
	CostOfCapital = Forecast("cost_of_capital_vessel_ammonia")
}
