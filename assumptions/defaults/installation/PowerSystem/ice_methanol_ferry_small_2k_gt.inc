# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

PowerSystem "ice_methanol_ferry_small_2k_gt" {
	Propulsion = Converter("propulsion_ice_methanol_ferry_small_2k_gt")
	Electrical = Converter("electrical_ice_methanol_ferry_small_2k_gt")
	Heat = Converter("heat_boiler_oil_ferry_small_2k_gt")

	CAPEX = Forecast("ferry_small_2k_gt_supply_system_methanol_capex")
	OPEX = <Forecast("ferry_small_2k_gt_supply_system_methanol_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
