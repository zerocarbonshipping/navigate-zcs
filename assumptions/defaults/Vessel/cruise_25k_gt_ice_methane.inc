# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Vessel "cruise_25k_gt_ice_methane" {
	
	PropulsionLoad = Curve("cruise_25k_gt_propulsion_load")
	ElectricalLoadAtSea = Variable("cruise_25k_gt_electrical_load_sea")
	ElectricalLoadInPort = Variable("cruise_25k_gt_electrical_load_port")
	HeatLoadAtSea = Variable("cruise_25k_gt_heat_load_sea")
	HeatLoadInPort = Variable("cruise_25k_gt_heat_load_port")
	
	PropulsionConverter = Converter("propulsion_ice_methane_cruise_25k_gt")
	ElectricalConverter = Converter("electrical_ice_methane_cruise_25k_gt")
	HeatConverter = Converter("heat_boiler_oil_cruise_25k_gt")
	Tanks = [Tank("main_methane_cruise_25k_gt"), Tank("pilot_oil_cruise_25k_gt")]
	
	Route = Route("operational_profile_cruise_25k_gt")
	NominalCapacity = Variable("cruise_25k_gt_nominal_capacity")
	Lifetime = Variable("cruise_25k_gt_lifetime")
	
	Capex = <Forecast("cruise_25k_gt_capex") + Forecast("cruise_25k_gt_supply_system_methane_capex")>
	Opex = <Forecast("cruise_25k_gt_opex") + Forecast("cruise_25k_gt_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
	CostOfCapital = Variable("cost_of_capital_vessel")
}
