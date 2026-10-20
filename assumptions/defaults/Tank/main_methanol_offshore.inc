# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methanol_offshore" {
	FuelTypes = METHANOL
	Size = Variable("tank_size_offshore")

	Capex = Forecast("tank_methanol_capex")
	Opex = <Forecast("tank_methanol_capex") * Variable("tank_opex_percentage_of_capex")>
}
