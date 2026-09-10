# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "tug_ice_ammonia" {
	
	PropulsionLoad = Curve("tug_propulsion_load")
	ElectricalLoadAtSea = Variable("tug_electrical_load_sea")
	ElectricalLoadInPort = Variable("tug_electrical_load_port")
	HeatLoadAtSea = Variable("tug_heat_load_sea")
	HeatLoadInPort = Variable("tug_heat_load_port")
	
	PowerSystem = PowerSystem("ice_ammonia_tug")
	Tanks = [Tank("main_ammonia_tug"), Tank("pilot_oil_tug")]
	
	Route = Route("operational_profile_tug")
	NominalCapacity = Variable("tug_nominal_capacity")
	Lifetime = Variable("tug_lifetime")
	
	Capex = Forecast("tug_capex")
	Opex = Forecast("tug_opex")
	CostOfCapital = Forecast("cost_of_capital_vessel_ammonia")
}
