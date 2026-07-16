# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------- PORTS --------------------------------------------------
#
# This file defines the key ports used in the example: one in Asia (Singapore)
# and multiple in Europe (Rotterdam, Hamburg, and Aalborg).
#
# These ports play a central role in shaping fuel availability and infrastructure limitations. 
# While major ports like Rotterdam and Singapore are equipped to handle a range of fuels 
# (including low-sulfur oil and bio-methanol), smaller ports like Aalborg may face 
# delays or be unable to adopt alternative fuel infrastructure.
#
# -------------------------------------------------------------------------------------

Port "singapore" {
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "rotterdam" {
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "hamburg" {
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "aalborg" {
    # Test how bio-methanol not being possible in Aalborg affects the output.
    set_bunkering_allowed("methanol_bio", FALSE)
}

Port "*" {
    set_bunkering_allowed("fossil_fuel_oil", TRUE)

    # Here we set the price and upstream emissions of LSFO as we don't calculate it bottom up.
	set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))

	set_handling_cost("fossil_fuel_oil", Variable("handling_cost_oil"))
    set_handling_cost("methanol_bio", Variable("handling_cost_methanol"))
}

# Here you can change the handling cost of oil and methanol
Variable "handling_cost_oil" {
	Value = 8
}

Variable "handling_cost_methanol" {
	Value = 18
}