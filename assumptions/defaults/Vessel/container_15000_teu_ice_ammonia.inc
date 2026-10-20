# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "container_15000_teu_ice_ammonia" {
	
	PropulsionLoad = Curve("container_15000_teu_propulsion_load")
	ElectricalLoadAtSea = Variable("container_15000_teu_electrical_load_sea")
	ElectricalLoadInPort = Variable("container_15000_teu_electrical_load_port")
	HeatLoadAtSea = Variable("container_15000_teu_heat_load_sea")
	HeatLoadInPort = Variable("container_15000_teu_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_ammonia_container_15000_teu")
	ElectricalConverter = Converter("electrical_ice_ammonia_container_15000_teu")
	HeatConverter = Converter("heat_boiler_oil_container_15000_teu")
	Tanks = [Tank("main_ammonia_container_15000_teu"), Tank("pilot_oil_container_15000_teu")]
	
	Route = Route("operational_profile_container_15000_teu")
	NominalCapacity = Variable("container_15000_teu_nominal_capacity")
	Lifetime = Variable("container_15000_teu_lifetime")
	
	Capex = <Forecast("container_15000_teu_capex") + Forecast("container_15000_teu_supply_system_ammonia_capex")>
	Opex = <Forecast("container_15000_teu_opex") + Forecast("container_15000_teu_supply_system_ammonia_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Forecast("cost_of_capital_vessel_ammonia")
}
