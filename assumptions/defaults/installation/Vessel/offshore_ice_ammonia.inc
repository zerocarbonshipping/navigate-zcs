# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "offshore_ice_ammonia" {
	
	PropulsionLoad = Curve("offshore_propulsion_load")
	ElectricalLoadAtSea = Variable("offshore_electrical_load_sea")
	ElectricalLoadInPort = Variable("offshore_electrical_load_port")
	HeatLoadAtSea = Variable("offshore_heat_load_sea")
	HeatLoadInPort = Variable("offshore_heat_load_port")
	
	PowerSystem = PowerSystem("ice_ammonia_offshore")
	Tanks = [Tank("main_ammonia_offshore"), Tank("pilot_oil_offshore")]
	
	Route = Route("operational_profile_offshore")
	NominalCapacity = Variable("offshore_nominal_capacity")
	Lifetime = Variable("offshore_lifetime")
	
	CAPEX = Forecast("offshore_capex")
	OPEX = Forecast("offshore_opex")
	CostOfCapital = Forecast("cost_of_capital_vessel_ammonia")
}
