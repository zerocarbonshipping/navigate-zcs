# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Producer "epc_fame_europe" {
	Plants = [Plant("plant_fatty_acid_methyl_ester_europe")]

	MaximumDevelopment = 1000 # Arbitrary/Unconstrained. Expected to be feedstock constrained rather than construction constrained.

	set_feed_constraint("used_cooking_oil", <Forecast("used_cooking_oil_availability_europe") * Forecast("used_cooking_oil_share_shipping")>)
}
