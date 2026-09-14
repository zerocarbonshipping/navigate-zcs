# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# All fuel-side prices and emissions pinned as explicit constants so upstream
# assumption changes cannot silently re-size the scenario. LNG is a
# liquid-market fuel (no Producer needed), so the destination fuel always has
# the supply surplus the conversion evaluation requires; the oil-vs-LNG price
# spread is the deck-sizing input driving the conversion business case.
Import Port "port_global"
Import Port "port_europe"

Port "*" {
	set_bunkering_allowed("fossil_fuel_oil", TRUE)
	set_bunkering_allowed("liquefied_natural_gas", TRUE)

	set_bunker_price_overwrite("fossil_fuel_oil", 550)                   # USD/ton
	set_bunker_price_overwrite("liquefied_natural_gas", 380)             # USD/ton

	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", 0.68)  # ton/ton fuel
	set_bunker_wtt_overwrite("liquefied_natural_gas", "carbon_dioxide", 0.45)
}

Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"
