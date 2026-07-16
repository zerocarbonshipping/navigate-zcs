# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_roro_7000_ceu" {
	FuelTypes = METHANE
	Size = Variable("tank_size_roro_7000_ceu")

	CAPEX = Forecast("tank_methane_capex_roro_7000_ceu")
	OPEX = <Forecast("tank_methane_capex_roro_7000_ceu") * Variable("tank_opex_percentage_of_capex")>
}
