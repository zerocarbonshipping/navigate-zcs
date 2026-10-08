# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_methanol_ferry_small_2k_gt" {
	FuelTypes = METHANOL
	Size = Variable("tank_size_ferry_small_2k_gt")

	CAPEX = Forecast("tank_methanol_capex")
	OPEX = <Forecast("tank_methanol_capex") * Variable("tank_opex_percentage_of_capex")>
}
