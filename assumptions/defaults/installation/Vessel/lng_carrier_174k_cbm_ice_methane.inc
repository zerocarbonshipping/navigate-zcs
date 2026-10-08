# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Vessel "lng_carrier_174k_cbm_ice_methane" {
	
	PropulsionLoad = Curve("lng_carrier_174k_cbm_propulsion_load")
	ElectricalLoadAtSea = Variable("lng_carrier_174k_cbm_electrical_load_sea")
	ElectricalLoadInPort = Variable("lng_carrier_174k_cbm_electrical_load_port")
	HeatLoadAtSea = Variable("lng_carrier_174k_cbm_heat_load_sea")
	HeatLoadInPort = Variable("lng_carrier_174k_cbm_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methane_lng_carrier_174k_cbm")
	Tanks = [Tank("main_methane_lng_carrier_174k_cbm"), Tank("pilot_oil_lng_carrier_174k_cbm")]
	
	Route = Route("operational_profile_lng_carrier_174k_cbm")
	NominalCapacity = Variable("lng_carrier_174k_cbm_nominal_capacity")
	Lifetime = Variable("lng_carrier_174k_cbm_lifetime")
	
	CAPEX = Forecast("lng_carrier_174k_cbm_capex")
	OPEX = Forecast("lng_carrier_174k_cbm_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
