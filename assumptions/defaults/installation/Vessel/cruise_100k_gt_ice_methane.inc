# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "cruise_100k_gt_ice_methane" {
	
	PropulsionLoad = Curve("cruise_100k_gt_propulsion_load")
	ElectricalLoadAtSea = Variable("cruise_100k_gt_electrical_load_sea")
	ElectricalLoadInPort = Variable("cruise_100k_gt_electrical_load_port")
	HeatLoadAtSea = Variable("cruise_100k_gt_heat_load_sea")
	HeatLoadInPort = Variable("cruise_100k_gt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_methane_cruise_100k_gt")
	Tanks = [Tank("main_methane_cruise_100k_gt"), Tank("pilot_oil_cruise_100k_gt")]
	
	Route = Route("operational_profile_cruise_100k_gt")
	NominalCapacity = Variable("cruise_100k_gt_nominal_capacity")
	Lifetime = Variable("cruise_100k_gt_lifetime")
	
	CAPEX = Forecast("cruise_100k_gt_capex")
	OPEX = Forecast("cruise_100k_gt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
