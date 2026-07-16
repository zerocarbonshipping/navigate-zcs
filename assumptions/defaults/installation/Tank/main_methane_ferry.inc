# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_ferry" {
	FuelTypes = METHANE
	Size = Variable("tank_size_ferry")

	CAPEX = Forecast("tank_methane_capex_ferry")
	OPEX = <Forecast("tank_methane_capex_ferry") * Variable("tank_opex_percentage_of_capex")>
}
