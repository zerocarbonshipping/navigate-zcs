# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "tanker_7500_dwt_ice_methane" {
	
	PropulsionLoad = Surface("tanker_7500_dwt_propulsion_load")
	ElectricalLoadAtSea = Variable("tanker_7500_dwt_electrical_load_sea")
	ElectricalLoadInPort = Variable("tanker_7500_dwt_electrical_load_port")
	HeatLoadAtSea = Variable("tanker_7500_dwt_heat_load_sea")
	HeatLoadInPort = Variable("tanker_7500_dwt_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methane_tanker_7500_dwt")
	ElectricalConverter = Converter("electrical_ice_methane_tanker_7500_dwt")
	HeatConverter = Converter("heat_boiler_oil_tanker_7500_dwt")
	Tanks = [Tank("main_methane_tanker_7500_dwt"), Tank("pilot_oil_tanker_7500_dwt")]
	
	Route = Route("operational_profile_tanker_7500_dwt")
	NominalCapacity = Variable("tanker_7500_dwt_nominal_capacity")
	Lifetime = Variable("tanker_7500_dwt_lifetime")
	
	Capex = <Forecast("tanker_7500_dwt_capex") + Forecast("tanker_7500_dwt_supply_system_methane_capex")>
	Opex = <Forecast("tanker_7500_dwt_opex") + Forecast("tanker_7500_dwt_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
