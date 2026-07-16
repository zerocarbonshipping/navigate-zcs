# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_oil_cruise_175k_gt" {
	Propulsion = Converter("propulsion_ice_oil_cruise_175k_gt")
	Electrical = Converter("electrical_ice_oil_cruise_175k_gt")
	Heat = Converter("heat_boiler_oil_cruise_175k_gt")

	CAPEX = Forecast("cruise_175k_gt_supply_system_oil_capex")
	OPEX = <Forecast("cruise_175k_gt_supply_system_oil_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
