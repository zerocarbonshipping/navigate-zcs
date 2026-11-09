# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# BUNKER LOGISTICS - production site to bunker port.
# Fuel oil and LNG are LiquidMarket fuels in the library: quoted price, no plant,
# no producer, no logistics chain (ports.inc). Every plant's fuel is shipped to
# both ports and picks up distance x rate.

Transport "fuel_shipping" {
}

Region "*" {
	# INVENTED: USD per ton per nautical mile
	set_transport_cost("fuel_shipping", 0.02)
}

Plant "*" {
	set_fuel_transport("*", Transport("fuel_shipping"))
}

# INVENTED: nautical miles from the production region to each port
Plant "plant_methanol_electro_alkaline" {
	set_fuel_distance("san_antonio", 1250)
	set_fuel_distance("rotterdam", 7600)
}

Plant "plant_ammonia_electro_alkaline" {
	set_fuel_distance("san_antonio", 1250)
	set_fuel_distance("rotterdam", 7600)
}

Plant "*_europe" {
	set_fuel_distance("rotterdam", 540)
	set_fuel_distance("san_antonio", 7600)
}

Plant "plant_methanol_bio_gasification" {
	set_fuel_distance("rotterdam", 540)
	set_fuel_distance("san_antonio", 7600)
}
