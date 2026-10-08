# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Vessel "ropax_25k_gt_ice_oil" {
	
	PropulsionLoad = Curve("ropax_25k_gt_propulsion_load")
	ElectricalLoadAtSea = Variable("ropax_25k_gt_electrical_load_sea")
	ElectricalLoadInPort = Variable("ropax_25k_gt_electrical_load_port")
	HeatLoadAtSea = Variable("ropax_25k_gt_heat_load_sea")
	HeatLoadInPort = Variable("ropax_25k_gt_heat_load_port")
	
	PowerSystem = PowerSystem("ice_oil_ropax_25k_gt")
	Tanks = [Tank("main_oil_ropax_25k_gt")]
	
	Route = Route("operational_profile_ropax_25k_gt")
	NominalCapacity = Variable("ropax_25k_gt_nominal_capacity")
	Lifetime = Variable("ropax_25k_gt_lifetime")
	
	CAPEX = Forecast("ropax_25k_gt_capex")
	OPEX = Forecast("ropax_25k_gt_opex")
	CostOfCapital = Variable("cost_of_capital_vessel")
}
