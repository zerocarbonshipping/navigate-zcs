# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "roro_4000_ceu_ice_methanol" {
	
	PropulsionLoad = Curve("roro_4000_ceu_propulsion_load")
	ElectricalLoadAtSea = Variable("roro_4000_ceu_electrical_load_sea")
	ElectricalLoadInPort = Variable("roro_4000_ceu_electrical_load_port")
	HeatLoadAtSea = Variable("roro_4000_ceu_heat_load_sea")
	HeatLoadInPort = Variable("roro_4000_ceu_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methanol_roro_4000_ceu")
	Tanks = [Tank("main_methanol_roro_4000_ceu"), Tank("pilot_oil_roro_4000_ceu")]
	
	Route = Route("operational_profile_roro_4000_ceu")
	NominalCapacity = Variable("roro_4000_ceu_nominal_capacity")
	Lifetime = Variable("roro_4000_ceu_lifetime")
	
	CAPEX = Forecast("roro_4000_ceu_capex")
	OPEX = Forecast("roro_4000_ceu_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
