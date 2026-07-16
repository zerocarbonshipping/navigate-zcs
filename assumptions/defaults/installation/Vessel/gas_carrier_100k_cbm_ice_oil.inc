# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "gas_carrier_100k_cbm_ice_oil" {
	
	PropulsionLoad = Curve("gas_carrier_100k_cbm_propulsion_load")
	ElectricalLoadAtSea = Variable("gas_carrier_100k_cbm_electrical_load_sea")
	ElectricalLoadInPort = Variable("gas_carrier_100k_cbm_electrical_load_port")
	HeatLoadAtSea = Variable("gas_carrier_100k_cbm_heat_load_sea")
	HeatLoadInPort = Variable("gas_carrier_100k_cbm_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_gas_carrier_100k_cbm")
	Tanks = [Tank("main_oil_gas_carrier_100k_cbm")]
	
	Route = Route("operational_profile_gas_carrier_100k_cbm")
	NominalCapacity = Variable("gas_carrier_100k_cbm_nominal_capacity")
	Lifetime = Variable("gas_carrier_100k_cbm_lifetime")
	
	CAPEX = Forecast("gas_carrier_100k_cbm_capex")
	OPEX = Forecast("gas_carrier_100k_cbm_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
