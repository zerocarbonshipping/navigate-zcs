# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "ferry_ice_methane" {
	
	PropulsionLoad = Curve("ferry_propulsion_load")
	ElectricalLoadAtSea = Variable("ferry_electrical_load_sea")
	ElectricalLoadInPort = Variable("ferry_electrical_load_port")
	HeatLoadAtSea = Variable("ferry_heat_load_sea")
	HeatLoadInPort = Variable("ferry_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methane_ferry")
	ElectricalConverter = Converter("electrical_ice_methane_ferry")
	HeatConverter = Converter("heat_boiler_oil_ferry")
	Tanks = [Tank("main_methane_ferry"), Tank("pilot_oil_ferry")]
	
	Route = Route("operational_profile_ferry")
	NominalCapacity = Variable("ferry_nominal_capacity")
	Lifetime = Variable("ferry_lifetime")
	
	Capex = <Forecast("ferry_capex") + Forecast("ferry_supply_system_methane_capex")>
	Opex = <Forecast("ferry_opex") + Forecast("ferry_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
