# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "general_cargo_ice_methanol" {
	
	PropulsionLoad = Curve("general_cargo_propulsion_load")
	ElectricalLoadAtSea = Variable("general_cargo_electrical_load_sea")
	ElectricalLoadInPort = Variable("general_cargo_electrical_load_port")
	HeatLoadAtSea = Variable("general_cargo_heat_load_sea")
	HeatLoadInPort = Variable("general_cargo_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methanol_general_cargo")
	ElectricalConverter = Converter("electrical_ice_methanol_general_cargo")
	HeatConverter = Converter("heat_boiler_oil_general_cargo")
	Tanks = [Tank("main_methanol_general_cargo"), Tank("pilot_oil_general_cargo")]
	
	Route = Route("operational_profile_general_cargo")
	NominalCapacity = Variable("general_cargo_nominal_capacity")
	Lifetime = Variable("general_cargo_lifetime")
	
	Capex = <Forecast("general_cargo_capex") + Forecast("general_cargo_supply_system_methanol_capex")>
	Opex = <Forecast("general_cargo_opex") + Forecast("general_cargo_supply_system_methanol_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
