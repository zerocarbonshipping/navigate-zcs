# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_general_cargo" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_general_cargo")

	CAPEX = Forecast("tank_ammonia_capex_general_cargo")
	OPEX = <Forecast("tank_ammonia_capex_general_cargo") * Variable("tank_opex_percentage_of_capex")>
}
