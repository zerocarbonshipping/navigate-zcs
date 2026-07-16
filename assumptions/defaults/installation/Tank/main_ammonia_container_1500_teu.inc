# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_container_1500_teu" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_container_1500_teu")

	CAPEX = Forecast("tank_ammonia_capex_container_1500_teu")
	OPEX = <Forecast("tank_ammonia_capex_container_1500_teu") * Variable("tank_opex_percentage_of_capex")>
}
