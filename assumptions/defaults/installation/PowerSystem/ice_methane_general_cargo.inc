# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

PowerSystem "ice_methane_general_cargo" {
	Propulsion = Converter("propulsion_ice_methane_general_cargo")
	Electrical = Converter("electrical_ice_methane_general_cargo")
	Heat = Converter("heat_boiler_oil_general_cargo")

	CAPEX = Forecast("general_cargo_supply_system_methane_capex")
	OPEX = <Forecast("general_cargo_supply_system_methane_capex") * Variable("supply_system_opex_percentage_of_capex")>
}
