# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PRODUCERS - who decides to build a fuel plant for this region's ships.
#
# The library's build rate and feedstock pools are global. This deck is a few
# hundred ships, so each producer gets a slice of them. Trinidad already makes
# about 5 Mt of ammonia and 6 Mt of methanol a year (The Energy Year, 2024), but
# grey and for export; the slices below are for new, low-emission plants serving
# these ships only.

Producer "producer_trinidad" {
	Plants = [Plant("plant_ammonia_blue"),
	          Plant("plant_ammonia_electro_alkaline"),
	          Plant("plant_methanol_electro_alkaline")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping") * Variable("caribbean_share_of_build")>

	set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("caribbean_share_of_feedstock")>)
}

# The US Gulf Coast builds for these ships too, out of the same slice of
# plant-building capacity as Trinidad (INVENTED, see below).
Producer "producer_americas" {
	Plants = [Plant("plant_methanol_bio_gasification"),
	          Plant("plant_ammonia_blue_americas"),
	          Plant("plant_ammonia_electro_alkaline_americas"),
	          Plant("plant_methanol_electro_alkaline_americas")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping") * Variable("caribbean_share_of_build")>

	set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("caribbean_share_of_feedstock")>)
	set_feed_constraint("feedstock_biomethanol_gasification", <Forecast("feedstock_biomethanol_gasification_availability") * Forecast("feedstock_biomethanol_gasification_share_shipping") * Variable("caribbean_share_of_feedstock")>)
}

# Chile builds e-fuels for these ships too, out of the same slice (INVENTED).
Producer "producer_chile" {
	Plants = [Plant("plant_ammonia_electro_alkaline_chile"),
	          Plant("plant_methanol_electro_alkaline_chile")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping") * Variable("caribbean_share_of_build")>

	set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("caribbean_share_of_feedstock")>)
}

# INVENTED: the region's share of shipping's plant-building capacity.
Variable "caribbean_share_of_build" {
	Value = 0.02
}

# INVENTED: the region's share of shipping's biogenic CO2 and biomass. CARES puts
# its domestic shipping at about 1 Mt CO2e a year, against roughly 1,000 Mt for
# world shipping, so 0.1 %; doubled for the international ships calling here.
Variable "caribbean_share_of_feedstock" {
	Value = 0.002
}
