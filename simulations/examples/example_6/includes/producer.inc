# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PRODUCERS - the agents that decide whether to build another plant. The library's
# feedstock ceilings are what all shipping may use; this fleet gets a share of them
# (GIVEN by the prompt: 0.02 of the used cooking oil and 0.02 of the biogenic CO2,
# in placeholders.inc). The library's biogenic CO2 pool is used as it is.

Producer "producer_fame" {
	Plants = [Plant("plant_fatty_acid_methyl_ester_europe")]

	# as the library's epc_fame_europe
	MaximumDevelopment = 1000

	set_feed_constraint("used_cooking_oil", <Forecast("used_cooking_oil_availability_europe") * Forecast("used_cooking_oil_share_shipping") * Variable("rhine_share_used_cooking_oil")>)
}

Producer "producer_efuel" {
	Plants = [Plant("plant_diesel_electro_alkaline_europe"),
	          Plant("plant_methanol_electro_alkaline_europe")]

	# as the library's epc_global
	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping")>

	set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("rhine_share_biogenic_carbon_dioxide")>)
}

# All fuel is made in Europe; where it is delivered follows bunker_logistics.inc.
Producer "*" {
	set_export_distribution("duisburg", 0.5)
	set_export_distribution("mannheim", 0.5)
}
