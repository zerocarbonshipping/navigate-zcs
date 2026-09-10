# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_tanker_300k_dwt" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_tanker_300k_dwt")

	Capex = Forecast("tank_ammonia_capex_tanker_300k_dwt")
	Opex = <Forecast("tank_ammonia_capex_tanker_300k_dwt") * Variable("tank_opex_percentage_of_capex")>
}
