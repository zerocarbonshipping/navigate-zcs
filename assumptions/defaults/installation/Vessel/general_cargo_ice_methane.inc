# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "general_cargo_ice_methane" {
	
	PropulsionLoad = Curve("general_cargo_propulsion_load")
	ElectricalLoadAtSea = Variable("general_cargo_electrical_load_sea")
	ElectricalLoadInPort = Variable("general_cargo_electrical_load_port")
	HeatLoadAtSea = Variable("general_cargo_heat_load_sea")
	HeatLoadInPort = Variable("general_cargo_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methane_general_cargo")
	Tanks = [Tank("main_methane_general_cargo"), Tank("pilot_oil_general_cargo")]
	
	Route = Route("operational_profile_general_cargo")
	NominalCapacity = Variable("general_cargo_nominal_capacity")
	Lifetime = Variable("general_cargo_lifetime")
	
	CAPEX = Forecast("general_cargo_capex")
	OPEX = Forecast("general_cargo_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
