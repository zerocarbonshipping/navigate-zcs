# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_cruise_100k_gt" {
	Propulsion = Converter("propulsion_ice_methane_cruise_100k_gt")
	Electrical = Converter("electrical_ice_methane_cruise_100k_gt")
	Heat = Converter("heat_boiler_oil_cruise_100k_gt")

	CAPEX = Forecast("cruise_100k_gt_supply_system_methane_capex")
	OPEX = <Forecast("cruise_100k_gt_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
