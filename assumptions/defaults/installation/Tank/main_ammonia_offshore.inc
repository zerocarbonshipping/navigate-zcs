# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_offshore" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_offshore")

	Capex = Forecast("tank_ammonia_capex_offshore")
	Opex = <Forecast("tank_ammonia_capex_offshore") * Variable("tank_opex_percentage_of_capex")>
}
