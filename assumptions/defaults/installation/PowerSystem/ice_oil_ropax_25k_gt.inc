# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

PowerSystem "ice_oil_ropax_25k_gt" {
	Propulsion = Converter("propulsion_ice_oil_ropax_25k_gt")
	Electrical = Converter("electrical_ice_oil_ropax_25k_gt")
	Heat = Converter("heat_boiler_oil_ropax_25k_gt")

	CAPEX = Forecast("ropax_25k_gt_supply_system_oil_capex")
	OPEX = <Forecast("ropax_25k_gt_supply_system_oil_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
