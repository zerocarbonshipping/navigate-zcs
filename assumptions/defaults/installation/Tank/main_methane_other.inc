# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_other" {
	FuelTypes = METHANE
	Size = Variable("tank_size_other")

	CAPEX = Forecast("tank_methane_capex_other")
	OPEX = <Forecast("tank_methane_capex_other") * Variable("tank_opex_percentage_of_capex")>
}
