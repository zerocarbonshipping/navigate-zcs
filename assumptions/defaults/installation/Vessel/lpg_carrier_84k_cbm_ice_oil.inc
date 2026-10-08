# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Vessel "lpg_carrier_84k_cbm_ice_oil" {
	
	PropulsionLoad = Curve("lpg_carrier_84k_cbm_propulsion_load")
	ElectricalLoadAtSea = Variable("lpg_carrier_84k_cbm_electrical_load_sea")
	ElectricalLoadInPort = Variable("lpg_carrier_84k_cbm_electrical_load_port")
	HeatLoadAtSea = Variable("lpg_carrier_84k_cbm_heat_load_sea")
	HeatLoadInPort = Variable("lpg_carrier_84k_cbm_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_lpg_carrier_84k_cbm")
	Tanks = [Tank("main_oil_lpg_carrier_84k_cbm")]
	
	Route = Route("operational_profile_lpg_carrier_84k_cbm")
	NominalCapacity = Variable("lpg_carrier_84k_cbm_nominal_capacity")
	Lifetime = Variable("lpg_carrier_84k_cbm_lifetime")
	
	CAPEX = Forecast("lpg_carrier_84k_cbm_capex")
	OPEX = Forecast("lpg_carrier_84k_cbm_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
