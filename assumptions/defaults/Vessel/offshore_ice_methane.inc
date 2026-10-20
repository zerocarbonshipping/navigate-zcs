# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "offshore_ice_methane" {
	
	PropulsionLoad = Curve("offshore_propulsion_load")
	ElectricalLoadAtSea = Variable("offshore_electrical_load_sea")
	ElectricalLoadInPort = Variable("offshore_electrical_load_port")
	HeatLoadAtSea = Variable("offshore_heat_load_sea")
	HeatLoadInPort = Variable("offshore_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methane_offshore")
	ElectricalConverter = Converter("electrical_ice_methane_offshore")
	HeatConverter = Converter("heat_boiler_oil_offshore")
	Tanks = [Tank("main_methane_offshore"), Tank("pilot_oil_offshore")]
	
	Route = Route("operational_profile_offshore")
	NominalCapacity = Variable("offshore_nominal_capacity")
	Lifetime = Variable("offshore_lifetime")
	
	Capex = <Forecast("offshore_capex") + Forecast("offshore_supply_system_methane_capex")>
	Opex = <Forecast("offshore_opex") + Forecast("offshore_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
