# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_general_cargo" {
	FuelTypes = METHANE
	Size = Variable("tank_size_general_cargo")

	CAPEX = Forecast("tank_methane_capex_general_cargo")
	OPEX = <Forecast("tank_methane_capex_general_cargo") * Variable("tank_opex_percentage_of_capex")>
}
