# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# PORTS - what can be bunkered where.
#
# Fossil fuel oil is sold everywhere at the library's global price. Balboa, the
# region's main bunkering port, averaged 511 USD/t VLSFO in 2025, close to
# Singapore (507.5) and 25 USD/t under the G20 index (Ship & Bunker, 2026).
#
# INVENTED: no Caribbean port bunkers LNG today; Jamaica has the region's
# regasification terminal (0.4 Bcf/d, US EIA), so LNG is offered there and in
# Miami only. The four new fuels can be bunkered at the three Caribbean ports,
# delivered from where they are made (bunker_logistics.inc). Miami offers
# fossil fuels only, so the feeders take their new fuels in the Caribbean.

Port "miami" {
    set_bunkering_allowed("liquefied_natural_gas", TRUE)
}

Port "jamaica" {
    set_bunkering_allowed("liquefied_natural_gas", TRUE)
    set_bunkering_allowed("ammonia_blue", TRUE)
    set_bunkering_allowed("ammonia_electro", TRUE)
    set_bunkering_allowed("methanol_electro", TRUE)
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "trinidad" {
    set_bunkering_allowed("ammonia_blue", TRUE)
    set_bunkering_allowed("ammonia_electro", TRUE)
    set_bunkering_allowed("methanol_electro", TRUE)
    set_bunkering_allowed("methanol_bio", TRUE)
}

Port "martinique" {
    set_bunkering_allowed("ammonia_blue", TRUE)
    set_bunkering_allowed("ammonia_electro", TRUE)
    set_bunkering_allowed("methanol_electro", TRUE)
    set_bunkering_allowed("methanol_bio", TRUE)
}

# Last, so it reaches every port above: a wildcard only applies to the ports
# that exist when it is read.
Port "*" {
    set_bunkering_allowed("fossil_fuel_oil", TRUE)
    set_bunker_price_overwrite("fossil_fuel_oil", Forecast("fossil_fuel_oil_price_global"))
    set_bunker_wtt_overwrite("fossil_fuel_oil", "carbon_dioxide", Forecast("fossil_fuel_oil_wtt_carbon_dioxide"))
    set_bunker_price_overwrite("liquefied_natural_gas", Forecast("liquefied_natural_gas_price_global"))
    set_bunker_wtt_overwrite("liquefied_natural_gas", "carbon_dioxide", Forecast("liquefied_natural_gas_wtt_carbon_dioxide"))
    set_bunker_wtt_overwrite("liquefied_natural_gas", "methane", Forecast("liquefied_natural_gas_wtt_methane"))
}
