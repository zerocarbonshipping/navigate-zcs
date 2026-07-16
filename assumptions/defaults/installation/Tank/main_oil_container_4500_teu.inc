# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_oil_container_4500_teu" {
	FuelTypes = OIL
	Size = Variable("tank_size_container_4500_teu")

	CAPEX = Forecast("tank_oil_capex")
	OPEX = <Forecast("tank_oil_capex") * Variable("tank_opex_percentage_of_capex")>
}
