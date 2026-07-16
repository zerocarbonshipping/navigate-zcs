# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_gas_carrier_100k_cbm" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_gas_carrier_100k_cbm")

	CAPEX = Forecast("tank_ammonia_capex_gas_carrier_100k_cbm")
	OPEX = <Forecast("tank_ammonia_capex_gas_carrier_100k_cbm") * Variable("tank_opex_percentage_of_capex")>
}
