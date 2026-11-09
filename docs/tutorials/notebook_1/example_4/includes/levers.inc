# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# LEVERS - Session 1's sensitivity levers, as placeholders that navigate fills in
# from --set NAME=VALUE. Each one re-assigns an input the other includes set, so
# this file comes last. A multiplier of 1 gives the reference, example_4.nav.

# ---- fuel prices ----
Port "*" {
    set_bunker_price_overwrite("fossil_fuel_oil", <Forecast("fossil_fuel_oil_price_global") * %OIL_PRICE%>)
    set_bunker_price_overwrite("liquefied_natural_gas", <Forecast("liquefied_natural_gas_price_global") * %LNG_PRICE%>)
}

# ---- regulation ----
Regulation "eu_ets" {
    RemedialCost = <Forecast("eu_ets_carbon_credit_price") * Forecast("eu_ets_maritime_phase_in") * %EU_ETS_PRICE%>
}

Regulation "fuel_eu" {
    # under 1 is stricter
    set_vessel_threshold("*", <Forecast("fuel_eu_target_reduction") * %FUELEU_TARGET%>)
    RemedialCost = <Variable("fuel_eu_remedial_cost") * %FUELEU_PENALTY%>
    # FALSE takes every ship out of FuelEU; EU ETS stays
    set_include_vessel("*", %FUELEU%)
}

# ---- fuel production ----
Region "americas" {
    set_source_opex("renewable", <Forecast("electricity_cost_americas_mid") * %CHILE_ELECTRICITY_PRICE%>)
    set_source_opex("grid", <Forecast("electricity_cost_americas_mid") * %CHILE_ELECTRICITY_PRICE%>)
}

Region "europe" {
    set_source_opex("renewable", <Forecast("electricity_cost_europe_mid") * %EUROPE_ELECTRICITY_PRICE%>)
    set_source_opex("grid", <Forecast("electricity_cost_europe_mid") * %EUROPE_ELECTRICITY_PRICE%>)
}

Producer "producer_biofuel" {
    set_feed_constraint("feedstock_biomethanol_gasification", <Forecast("feedstock_biomethanol_gasification_availability") * Forecast("feedstock_biomethanol_gasification_share_shipping") * Variable("trade_share_gasifiable_biomass") * %BIOMASS_AVAILABILITY%>)
}

Producer "producer_efuel" {
    set_feed_constraint("carbon_dioxide_biogenic", <Forecast("carbon_dioxide_biogenic_availability_flat") * Forecast("carbon_dioxide_biogenic_share_shipping") * Variable("trade_share_biogenic_carbon_dioxide") * %BIOGENIC_CO2_AVAILABILITY%>)
}

# ---- the owners ----
Fleet "copper_trade" {
    # 0 keeps trade at its 2026 volume, -1 shrinks it as fast as it would have grown
    TradeGrowth = <Forecast("trade_growth_bulk_carrier") * %TRADE_GROWTH%>

    # the share of the fleet that may fit each efficiency technology in a year,
    # on newbuilds and on retrofits; 1 is Navigate's default, 0 freezes efficiency
    set_newbuild_technology_limit("*", %TECHNOLOGY_LIMIT%)
    set_retrofit_technology_limit("*", %TECHNOLOGY_LIMIT%)
}
