# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_tug" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_tug")

	CAPEX = Forecast("tank_ammonia_capex_tug")
	OPEX = <Forecast("tank_ammonia_capex_tug") * Variable("tank_opex_percentage_of_capex")>
}
