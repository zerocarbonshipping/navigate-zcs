# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_ferry" {
	FuelTypes = METHANE
	Volume = Variable("tank_size_ferry")

	Capex = Forecast("tank_methane_capex_ferry")
	Opex = <Forecast("tank_methane_capex_ferry") * Variable("tank_opex_percentage_of_capex")>
}
