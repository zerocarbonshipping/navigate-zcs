# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Tank "main_ammonia_cruise_100k_gt" {
	FuelTypes = AMMONIA
	Size = Variable("tank_size_cruise_100k_gt")

	CAPEX = Forecast("tank_ammonia_capex_cruise_100k_gt")
	OPEX = <Forecast("tank_ammonia_capex_cruise_100k_gt") * Variable("tank_opex_percentage_of_capex")>
}
