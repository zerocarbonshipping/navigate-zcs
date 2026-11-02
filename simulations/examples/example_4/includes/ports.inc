# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PORTS - what can be bunkered where. Both ports sell the same five fuels: fuel
# oil, LNG, e-ammonia, e-methanol and bio-methanol. A fuel is shipped from the
# region that made it to the port that needs it, the same way Chilean e-ammonia
# reaches Rotterdam.
# Delivered price is production cost plus transport, set in bunker_logistics.inc.

Port "san_antonio" {
    set_bunkering_allowed("methanol_electro", TRUE)
    set_bunkering_allowed("ammonia_electro", TRUE)
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "rotterdam" {
    set_bunkering_allowed("methanol_electro", TRUE)
    set_bunkering_allowed("ammonia_electro", TRUE)
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "*" {
    # the two fossil fuels are treated as globally traded and available anywhere
    set_bunkering_allowed("fossil_fuel_oil", TRUE)
    set_bunkering_allowed("liquefied_natural_gas", TRUE)

    # Fossil prices and upstream emissions are taken as given rather than built
    # bottom-up from a production pathway.
    set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
    set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))
    set_bunker_price_overwrite("liquefied_natural_gas", Forecast("liquefied_natural_gas_price_global"))
    set_bunker_wtt_overwrite("liquefied_natural_gas", "carbon_dioxide", Forecast("liquefied_natural_gas_wtt_carbon_dioxide"))
    set_bunker_wtt_overwrite("liquefied_natural_gas", "methane", Forecast("liquefied_natural_gas_wtt_methane"))

    # Cost of physically getting the fuel aboard, USD/ton: a fixed cost per ton
    # for storage and the bunkering service. These per-ton charges are the only
    # infrastructure costs in Navigate: terminals, storage tanks and bunker
    # vessels have no investment cost and are never built. A slow or costly port
    # build-out has to be entered by hand: set_bunkering_allowed or
    # set_bunkering_limit for when and how much a port can deliver, and a higher
    # or time-varying handling cost for what it costs.
    set_handling_cost("fossil_fuel_oil", Variable("handling_cost_oil"))
    set_handling_cost("liquefied_natural_gas", Variable("handling_cost_lng"))
    set_handling_cost("methanol_electro", Variable("handling_cost_methanol"))
    set_handling_cost("methanol_bio", Variable("handling_cost_methanol"))
    set_handling_cost("ammonia_electro", Variable("handling_cost_ammonia"))
}

# Values are invented for this example.
Variable "handling_cost_oil" {
	Value = 8
}

Variable "handling_cost_lng" {
	Value = 15
}

Variable "handling_cost_methanol" {
	Value = 18
}

Variable "handling_cost_ammonia" {
	Value = 25
}
