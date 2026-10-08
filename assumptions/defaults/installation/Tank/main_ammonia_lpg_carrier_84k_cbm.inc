# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# structure inherited from gas_carrier_100k_cbm: same fuel, converter and tank combinations,
# owner to confirm (Ship Design & Technology).

Tank "main_ammonia_lpg_carrier_84k_cbm" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_lpg_carrier_84k_cbm")

	CAPEX = Forecast("tank_ammonia_capex_lpg_carrier_84k_cbm")
	OPEX = <Forecast("tank_ammonia_capex_lpg_carrier_84k_cbm") * Variable("tank_opex_percentage_of_capex")>
}
