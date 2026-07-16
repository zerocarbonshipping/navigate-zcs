# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methanol_cruise_175k_gt" {
	FuelTypes = METHANOL
	Size = Variable("tank_size_cruise_175k_gt")

	CAPEX = Forecast("tank_methanol_capex")
	OPEX = <Forecast("tank_methanol_capex") * Variable("tank_opex_percentage_of_capex")>
}
