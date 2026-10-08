# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from ferry: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_ammonia_ropax_25k_gt" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_ropax_25k_gt")

	CAPEX = Forecast("tank_ammonia_capex_ropax_25k_gt")
	OPEX = <Forecast("tank_ammonia_capex_ropax_25k_gt") * Variable("tank_opex_percentage_of_capex")>
}
