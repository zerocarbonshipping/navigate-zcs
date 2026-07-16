# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------- PORTS --------------------------------------------------
#
# This file defines the set of ports used in the Baltic tanker example:
# Helsinki, Stockholm, Tallinn, and Gdansk.
#
# Helsinki serves as the operators' base and a primary bunkering hub, where
# both fossil fuels and e-ammonia are assumed to be available.
# Stockholm is included as a secondary hub, also offering access to e-ammonia 
# alongside fossil fuels. 
#
# Tallinn and Gdansk represent ports where bunkering infrastructure is assumed 
# to remain fossil-only, reflecting a slower uptake of e-ammonia outside the 
# main hubs. This creates the need for careful bunkering logistics when 
# operating across the network. 
#
# Port definitions capture differences in fuel availability and handling costs.
 # These assumptions are important for modeling the transition
# from fossil fuels to electro-fuels under combined IMO and EU regulatory 
# frameworks, and for illustrating the challenges faced by a regional tanker 
# operator in the Baltic.
#
# -------------------------------------------------------------------------------------

Port "helsinki" {
    set_bunkering_allowed("ammonia_electro", TRUE)
}

Port "stockholm" {
    set_bunkering_allowed("ammonia_electro", TRUE)
}

Port "tallinn" {
    set_bunkering_allowed("ammonia_electro", FALSE)
}

Port "gdansk" {
    set_bunkering_allowed("ammonia_electro", FALSE)
}

Port "*" {
    set_bunkering_allowed("fossil_fuel_oil", TRUE)

    # Here we overwrite to define the price and WTT of LSFO as we don't calculate it bottom up. 
	set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
	set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))

	set_handling_cost("fossil_fuel_oil", Variable("handling_cost_oil"))
    set_handling_cost("ammonia_electro", Variable("handling_cost_ammonia"))
}

# Here you can change the handling cost of oil and ammonia
Variable "handling_cost_oil" {
	Value = 8
}

Variable "handling_cost_ammonia" {
	Value = 25
}