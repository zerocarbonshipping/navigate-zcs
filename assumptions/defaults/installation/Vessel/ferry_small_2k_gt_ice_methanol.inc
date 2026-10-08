# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Vessel "ferry_small_2k_gt_ice_methanol" {
	
	PropulsionLoad = Curve("ferry_small_2k_gt_propulsion_load")
	ElectricalLoadAtSea = Variable("ferry_small_2k_gt_electrical_load_sea")
	ElectricalLoadInPort = Variable("ferry_small_2k_gt_electrical_load_port")
	HeatLoadAtSea = Variable("ferry_small_2k_gt_heat_load_sea")
	HeatLoadInPort = Variable("ferry_small_2k_gt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methanol_ferry_small_2k_gt")
	Tanks = [Tank("main_methanol_ferry_small_2k_gt"), Tank("pilot_oil_ferry_small_2k_gt")]
	
	Route = Route("operational_profile_ferry_small_2k_gt")
	NominalCapacity = Variable("ferry_small_2k_gt_nominal_capacity")
	Lifetime = Variable("ferry_small_2k_gt_lifetime")
	
	CAPEX = Forecast("ferry_small_2k_gt_capex")
	OPEX = Forecast("ferry_small_2k_gt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
