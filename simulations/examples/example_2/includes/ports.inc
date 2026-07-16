# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------- PORTS --------------------------------------------------
#
# This file defines the simplified set of ports used in the example: Australia,
# New Zealand, Fiji, Samoa, and Tonga. 
#
# Australia and New Zealand act as regional hubs with full fuel supply, including 
# both fossil fuel oils and FAME biofuel. Fiji, Samoa, and Tonga represent
# smaller island ports with more limited bunkering options, where only fossil fuels 
# are assumed to be available. 
#
# -------------------------------------------------------------------------------------

Port "australia" {
    set_bunkering_allowed("fatty_acid_methyl_ester", TRUE)
}

Port "new_zealand" {
    set_bunkering_allowed("fatty_acid_methyl_ester", TRUE)
}

Port "fiji" {
    set_bunkering_allowed("fatty_acid_methyl_ester", FALSE)
}

Port "samoa" {
    set_bunkering_allowed("fatty_acid_methyl_ester", FALSE)
}

Port "tonga" {
    set_bunkering_allowed("fatty_acid_methyl_ester", FALSE)
}

Port "*" {
    set_bunkering_allowed("fossil_fuel_oil", TRUE)

    # Here we define the price and WTT of fossil fuel oil as we don't calculate it bottom up.
	set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))

	set_handling_cost("fossil_fuel_oil", Variable("handling_cost_oil"))
    set_handling_cost("fatty_acid_methyl_ester", Variable("handling_cost_fame"))
}

# Here you can change the handling cost of oil and fame
Variable "handling_cost_oil" {
	Value = 8
}

Variable "handling_cost_fame" {
	Value = 18
}