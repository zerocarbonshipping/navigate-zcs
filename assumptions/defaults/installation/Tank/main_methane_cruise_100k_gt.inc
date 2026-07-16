# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_cruise_100k_gt" {
	FuelTypes = METHANE
	Size = Variable("tank_size_cruise_100k_gt")

	CAPEX = Forecast("tank_methane_capex_cruise_100k_gt")
	OPEX = <Forecast("tank_methane_capex_cruise_100k_gt") * Variable("tank_opex_percentage_of_capex")>
}
