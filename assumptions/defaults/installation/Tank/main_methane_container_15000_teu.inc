# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_methane_container_15000_teu" {
	FuelTypes = METHANE
	Size = Variable("tank_size_container_15000_teu")

	CAPEX = Forecast("tank_methane_capex_container_15000_teu")
	OPEX = <Forecast("tank_methane_capex_container_15000_teu") * Variable("tank_opex_percentage_of_capex")>
}
