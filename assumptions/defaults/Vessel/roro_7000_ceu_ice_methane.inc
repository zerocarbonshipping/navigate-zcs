# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "roro_7000_ceu_ice_methane" {
	
	PropulsionLoad = Curve("roro_7000_ceu_propulsion_load")
	ElectricalLoadAtSea = Variable("roro_7000_ceu_electrical_load_sea")
	ElectricalLoadInPort = Variable("roro_7000_ceu_electrical_load_port")
	HeatLoadAtSea = Variable("roro_7000_ceu_heat_load_sea")
	HeatLoadInPort = Variable("roro_7000_ceu_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methane_roro_7000_ceu")
	ElectricalConverter = Converter("electrical_ice_methane_roro_7000_ceu")
	HeatConverter = Converter("heat_boiler_oil_roro_7000_ceu")
	Tanks = [Tank("main_methane_roro_7000_ceu"), Tank("pilot_oil_roro_7000_ceu")]
	
	Route = Route("operational_profile_roro_7000_ceu")
	NominalCapacity = Variable("roro_7000_ceu_nominal_capacity")
	Lifetime = Variable("roro_7000_ceu_lifetime")
	
	Capex = <Forecast("roro_7000_ceu_capex") + Forecast("roro_7000_ceu_supply_system_methane_capex")>
	Opex = <Forecast("roro_7000_ceu_opex") + Forecast("roro_7000_ceu_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
