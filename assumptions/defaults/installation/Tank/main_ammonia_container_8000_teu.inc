# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_container_8000_teu" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_container_8000_teu")

	CAPEX = Forecast("tank_ammonia_capex_container_8000_teu")
	OPEX = <Forecast("tank_ammonia_capex_container_8000_teu") * Variable("tank_opex_percentage_of_capex")>
}
