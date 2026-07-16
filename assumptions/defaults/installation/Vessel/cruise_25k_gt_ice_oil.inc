# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "cruise_25k_gt_ice_oil" {
	
	PropulsionLoad = Curve("cruise_25k_gt_propulsion_load")
	ElectricalLoadAtSea = Variable("cruise_25k_gt_electrical_load_sea")
	ElectricalLoadInPort = Variable("cruise_25k_gt_electrical_load_port")
	HeatLoadAtSea = Variable("cruise_25k_gt_heat_load_sea")
	HeatLoadInPort = Variable("cruise_25k_gt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_cruise_25k_gt")
	Tanks = [Tank("main_oil_cruise_25k_gt")]
	
	Route = Route("operational_profile_cruise_25k_gt")
	NominalCapacity = Variable("cruise_25k_gt_nominal_capacity")
	Lifetime = Variable("cruise_25k_gt_lifetime")
	
	CAPEX = Forecast("cruise_25k_gt_capex")
	OPEX = Forecast("cruise_25k_gt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
