# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_offshore" {
	FuelTypes = METHANE
	Size = Variable("tank_size_offshore")

	CAPEX = Forecast("tank_methane_capex_offshore")
	OPEX = <Forecast("tank_methane_capex_offshore") * Variable("tank_opex_percentage_of_capex")>
}
