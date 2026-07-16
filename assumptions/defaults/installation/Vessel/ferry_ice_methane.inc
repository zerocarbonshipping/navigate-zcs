# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "ferry_ice_methane" {
	
	PropulsionLoad = Curve("ferry_propulsion_load")
	ElectricalLoadAtSea = Variable("ferry_electrical_load_sea")
	ElectricalLoadInPort = Variable("ferry_electrical_load_port")
	HeatLoadAtSea = Variable("ferry_heat_load_sea")
	HeatLoadInPort = Variable("ferry_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methane_ferry")
	Tanks = [Tank("main_methane_ferry"), Tank("pilot_oil_ferry")]
	
	Route = Route("operational_profile_ferry")
	NominalCapacity = Variable("ferry_nominal_capacity")
	Lifetime = Variable("ferry_lifetime")
	
	CAPEX = Forecast("ferry_capex")
	OPEX = Forecast("ferry_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
