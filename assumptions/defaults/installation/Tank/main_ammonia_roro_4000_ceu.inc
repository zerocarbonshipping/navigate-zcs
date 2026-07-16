# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_roro_4000_ceu" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_roro_4000_ceu")

	CAPEX = Forecast("tank_ammonia_capex_roro_4000_ceu")
	OPEX = <Forecast("tank_ammonia_capex_roro_4000_ceu") * Variable("tank_opex_percentage_of_capex")>
}
