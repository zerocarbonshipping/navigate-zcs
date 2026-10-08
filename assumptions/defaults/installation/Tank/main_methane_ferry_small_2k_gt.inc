# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_methane_ferry_small_2k_gt" {
	FuelTypes = METHANE
	Size = Variable("tank_size_ferry_small_2k_gt")

	CAPEX = Forecast("tank_methane_capex_ferry_small_2k_gt")
	OPEX = <Forecast("tank_methane_capex_ferry_small_2k_gt") * Variable("tank_opex_percentage_of_capex")>
}
