# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "cruise_175k_gt_ice_oil" {
	
	PropulsionLoad = Curve("cruise_175k_gt_propulsion_load")
	ElectricalLoadAtSea = Variable("cruise_175k_gt_electrical_load_sea")
	ElectricalLoadInPort = Variable("cruise_175k_gt_electrical_load_port")
	HeatLoadAtSea = Variable("cruise_175k_gt_heat_load_sea")
	HeatLoadInPort = Variable("cruise_175k_gt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_cruise_175k_gt")
	Tanks = [Tank("main_oil_cruise_175k_gt")]
	
	Route = Route("operational_profile_cruise_175k_gt")
	NominalCapacity = Variable("cruise_175k_gt_nominal_capacity")
	Lifetime = Variable("cruise_175k_gt_lifetime")
	
	CAPEX = Forecast("cruise_175k_gt_capex")
	OPEX = Forecast("cruise_175k_gt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
