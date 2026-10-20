# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "roro_4000_ceu_ice_oil" {
	
	PropulsionLoad = Curve("roro_4000_ceu_propulsion_load")
	ElectricalLoadAtSea = Variable("roro_4000_ceu_electrical_load_sea")
	ElectricalLoadInPort = Variable("roro_4000_ceu_electrical_load_port")
	HeatLoadAtSea = Variable("roro_4000_ceu_heat_load_sea")
	HeatLoadInPort = Variable("roro_4000_ceu_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_oil_roro_4000_ceu")
	ElectricalConverter = Converter("electrical_ice_oil_roro_4000_ceu")
	HeatConverter = Converter("heat_boiler_oil_roro_4000_ceu")
	Tanks = [Tank("main_oil_roro_4000_ceu")]
	
	Route = Route("operational_profile_roro_4000_ceu")
	NominalCapacity = Variable("roro_4000_ceu_nominal_capacity")
	Lifetime = Variable("roro_4000_ceu_lifetime")
	
	Capex = <Forecast("roro_4000_ceu_capex") + Forecast("roro_4000_ceu_supply_system_oil_capex")>
	Opex = <Forecast("roro_4000_ceu_opex") + Forecast("roro_4000_ceu_supply_system_oil_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
