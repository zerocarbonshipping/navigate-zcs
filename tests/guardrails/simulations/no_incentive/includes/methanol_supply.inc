# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Bio-methanol supply chain with pinned economics, plus ample-supply
# overrides: this deck isolates the newbuild choice model, so supply must
# never be the reason a fuel gets a small share. The e-ammonia chain is
# shared from ../0_includes/fuel_supply_ammonia.inc.

# LNG imports LiquidMarket = TRUE from the defaults: available without a
# Producer, priced and emission-rated at the ports
Import Fuel "liquefied_natural_gas"

Import Fuel "methanol_bio"

Import Plant "plant_methanol_bio_gasification"

Plant "plant_methanol_bio_gasification" {
	Region = Region("europe")
	Source = Source("renewable")

	# pinned sizing (LeadTime/Lifetime from the bio-plant defaults, which
	# differ from the electro-ammonia plant's)
	Capacity = 1000      # ton/day
	LeadTime = 3         # years
	Lifetime = 20        # years
	Uptime = 0.9
}

Import Process "methanol_synthesis_bio_gasification"
Import Feedstock "feedstock_biomethanol_gasification"

Producer "producer_methanol" {
	Plants = [Plant("plant_methanol_bio_gasification")]

	MaximumDevelopment = 100

	set_export_distribution("port_global", 1.)
}

# ample supply for the shared ammonia chain as well
Producer "epc_europe" {
	MaximumDevelopment = 100
}

# pinned production economics (USD/ton unless noted)
Region "europe" {
	set_feedstock_cost("feedstock_biomethanol_gasification", 65)

	set_process_capex("methanol_synthesis_bio_gasification", 2500)
	set_process_opex("methanol_synthesis_bio_gasification", 400)
	set_process_energy("methanol_synthesis_bio_gasification", 0.52)   # MWh/ton
}
