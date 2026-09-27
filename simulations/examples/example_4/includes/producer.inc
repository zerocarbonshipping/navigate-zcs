# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PRODUCERS - the agents that decide whether to build another plant.

Producer "producer_efuel" {
	Plants = [Plant("plant_methanol_electro_alkaline"),
	          Plant("plant_ammonia_electro_alkaline"),
	          Plant("plant_methanol_electro_alkaline_europe"),
	          Plant("plant_ammonia_electro_alkaline_europe")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping")>

	# Ceiling on biogenic CO2, the feedstock both its e-methanol plants draw on.

	set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("trade_share_biogenic_carbon_dioxide")>)
}

Producer "producer_biofuel" {
	Plants = [Plant("plant_methanol_bio_gasification")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping")>

	# Ceiling on gasifiable biomass.
	set_feed_constraint("feedstock_biomethanol_gasification", <Forecast("feedstock_biomethanol_gasification_availability") * Forecast("feedstock_biomethanol_gasification_share_shipping") * Variable("trade_share_gasifiable_biomass")>)
}

# The library's feedstock forecasts are global and its *_share_shipping factors
# are the whole sector's slice. This deck is 300 ships on one trade, not the
# world fleet, so each producer gets a slice of that. Both shares are
# invented for this example.
Variable "trade_share_gasifiable_biomass" {
	Value = 0.01
}

Variable "trade_share_biogenic_carbon_dioxide" {
	Value = 0.003
}
