# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "other_ice_ammonia" {
	
	PropulsionLoad = Curve("other_propulsion_load")
	ElectricalLoadAtSea = Variable("other_electrical_load_sea")
	ElectricalLoadInPort = Variable("other_electrical_load_port")
	HeatLoadAtSea = Variable("other_heat_load_sea")
	HeatLoadInPort = Variable("other_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_ammonia_other")
	ElectricalConverter = Converter("electrical_ice_ammonia_other")
	HeatConverter = Converter("heat_boiler_oil_other")
	Tanks = [Tank("main_ammonia_other"), Tank("pilot_oil_other")]
	
	Route = Route("operational_profile_other")
	NominalCapacity = Variable("other_nominal_capacity")
	Lifetime = Variable("other_lifetime")
	
	Capex = <Forecast("other_capex") + Forecast("other_supply_system_ammonia_capex")>
	Opex = <Forecast("other_opex") + Forecast("other_supply_system_ammonia_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Forecast("cost_of_capital_vessel_ammonia")
}
