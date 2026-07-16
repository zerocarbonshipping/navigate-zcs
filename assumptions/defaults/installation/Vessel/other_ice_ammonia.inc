# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "other_ice_ammonia" {
	
	PropulsionLoad = Curve("other_propulsion_load")
	ElectricalLoadAtSea = Variable("other_electrical_load_sea")
	ElectricalLoadInPort = Variable("other_electrical_load_port")
	HeatLoadAtSea = Variable("other_heat_load_sea")
	HeatLoadInPort = Variable("other_heat_load_port")
	
	PowerSystem = PowerSystem("ice_ammonia_other")
	Tanks = [Tank("main_ammonia_other"), Tank("pilot_oil_other")]
	
	Route = Route("operational_profile_other")
	NominalCapacity = Variable("other_nominal_capacity")
	Lifetime = Variable("other_lifetime")
	
	CAPEX = Forecast("other_capex")
	OPEX = Forecast("other_opex")
	CostOfCapital = Forecast("cost_of_capital_vessel_ammonia")
}
