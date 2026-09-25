# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PRODUCERS - the agents that decide whether to build another plant.
#
# Ownership is by FUEL FAMILY, not by geography. A Producer in Navigate is an EPC
# market rather than a place, so the e-fuel producer builds wherever a site is
# cheapest delivered - and because it owns two plants making the same fuel, it
# has a choice to make between them on delivered cost.

Producer "producer_efuel" {
	Plants = [Plant("plant_methanol_electro_alkaline"),
	          Plant("plant_ammonia_electro_alkaline"),
	          Plant("plant_methanol_electro_alkaline_europe"),
	          Plant("plant_ammonia_electro_alkaline_europe")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping")>

	# Ceiling on biogenic CO2, the feedstock both its e-methanol plants draw on.
	# This one only bites at the end: no e-methanol is built before 2040, and the
	# draw then tracks the ceiling through the 2040s before reaching it in 2049.
	set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("trade_share_biogenic_carbon_dioxide")>)
}

Producer "producer_biofuel" {
	Plants = [Plant("plant_methanol_bio_gasification")]

	MaximumDevelopment = <Forecast("epc_global_capacity_mid") * Forecast("epc_global_share_shipping")>

	# Ceiling on gasifiable biomass. This one BINDS: it roughly halves the
	# bio-methanol this trade can source, so the fuel is limited by what can be
	# grown rather than by what the ships would buy.
	set_feed_constraint("feedstock_biomethanol_gasification", <Forecast("feedstock_biomethanol_gasification_availability") * Forecast("feedstock_biomethanol_gasification_share_shipping") * Variable("trade_share_gasifiable_biomass")>)
}

# The library's feedstock forecasts are global and its *_share_shipping factors
# are the whole sector's slice. This deck is 300 ships on one trade, not the
# world fleet, so each producer gets a slice of that in turn. Both shares are
# invented for this example, and both are set where they start to bite: biomass
# from 2038, biogenic CO2 only in the last years.
Variable "trade_share_gasifiable_biomass" {
	Value = 0.01
}

Variable "trade_share_biogenic_carbon_dioxide" {
	Value = 0.003
}
