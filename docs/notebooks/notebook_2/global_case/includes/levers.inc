# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# LEVERS - Session 2's levers every scenario holds, as placeholders that navigate
# fills in from --set NAME=VALUE. Each multiplies a library forecast, whose own
# Multiplier is 1; the deck holds a forecast only once it is imported. The
# regulation levers are in eu_levers.inc and global_standard_levers.inc.

# ---- fuel prices ----
Import Forecast "fossil_fuel_oil_price_global"
Forecast "fossil_fuel_oil_price_global" {
    Multiplier = %OIL_PRICE%
}

Import Forecast "liquefied_natural_gas_price_global"
Forecast "liquefied_natural_gas_price_global" {
    Multiplier = %LNG_PRICE%
}

# ---- fuel production ----
# the renewable and grid electricity of all five regions
Import Forecast "electricity_cost_africa_mid"
Forecast "electricity_cost_africa_mid" {
    Multiplier = %EFUEL_ELECTRICITY_PRICE%
}

Import Forecast "electricity_cost_americas_mid"
Forecast "electricity_cost_americas_mid" {
    Multiplier = %EFUEL_ELECTRICITY_PRICE%
}

Import Forecast "electricity_cost_asia_mid"
Forecast "electricity_cost_asia_mid" {
    Multiplier = %EFUEL_ELECTRICITY_PRICE%
}

Import Forecast "electricity_cost_europe_mid"
Forecast "electricity_cost_europe_mid" {
    Multiplier = %EFUEL_ELECTRICITY_PRICE%
}

Import Forecast "electricity_cost_middle_east_mid"
Forecast "electricity_cost_middle_east_mid" {
    Multiplier = %EFUEL_ELECTRICITY_PRICE%
}

# the share of each feedstock pool that shipping may use
Import Forecast "carbon_dioxide_biogenic_share_shipping"
Forecast "carbon_dioxide_biogenic_share_shipping" {
    Multiplier = %BIOMASS_SHARE_FOR_SHIPPING%
}

Import Forecast "feedstock_bioethanol_fermentation_share_shipping"
Forecast "feedstock_bioethanol_fermentation_share_shipping" {
    Multiplier = %BIOMASS_SHARE_FOR_SHIPPING%
}

Import Forecast "feedstock_biogas_share_shipping"
Forecast "feedstock_biogas_share_shipping" {
    Multiplier = %BIOMASS_SHARE_FOR_SHIPPING%
}

Import Forecast "feedstock_biomethanol_gasification_share_shipping"
Forecast "feedstock_biomethanol_gasification_share_shipping" {
    Multiplier = %BIOMASS_SHARE_FOR_SHIPPING%
}

Import Forecast "used_cooking_oil_share_shipping"
Forecast "used_cooking_oil_share_shipping" {
    Multiplier = %BIOMASS_SHARE_FOR_SHIPPING%
}

# the plants (not bio-fuel plants) that may be built a year
Import Forecast "epc_global_capacity_mid"
Forecast "epc_global_capacity_mid" {
    Multiplier = %PLANT_BUILD_LIMIT%
}

# ---- the owners ----
# 0 keeps trade at its 2026 volume, -1 shrinks it as fast as it would have grown
Import Forecast "trade_growth_bulk_carrier"
Forecast "trade_growth_bulk_carrier" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_container_15000_teu"
Forecast "trade_growth_container_15000_teu" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_container_1500_teu"
Forecast "trade_growth_container_1500_teu" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_container_4500_teu"
Forecast "trade_growth_container_4500_teu" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_container_8000_teu"
Forecast "trade_growth_container_8000_teu" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_cruise"
Forecast "trade_growth_cruise" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_ferry"
Forecast "trade_growth_ferry" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_gas_carrier"
Forecast "trade_growth_gas_carrier" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_general_cargo"
Forecast "trade_growth_general_cargo" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_offshore"
Forecast "trade_growth_offshore" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_other"
Forecast "trade_growth_other" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_roro"
Forecast "trade_growth_roro" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_tanker"
Forecast "trade_growth_tanker" {
    Multiplier = %TRADE_GROWTH%
}

Import Forecast "trade_growth_tug"
Forecast "trade_growth_tug" {
    Multiplier = %TRADE_GROWTH%
}

# the share of the fleet that may fit each efficiency technology in a year, on
# newbuilds and on retrofits; 1 is Navigate's default, 0 freezes efficiency.
# Only these segments' fleets have efficiency technologies.

Fleet "bulk_carrier_*" {
    set_newbuild_technology_limit("*", %TECHNOLOGY_LIMIT%)
    set_retrofit_technology_limit("*", %TECHNOLOGY_LIMIT%)
}

Fleet "container_*" {
    set_newbuild_technology_limit("*", %TECHNOLOGY_LIMIT%)
    set_retrofit_technology_limit("*", %TECHNOLOGY_LIMIT%)
}

Fleet "gas_carrier_*" {
    set_newbuild_technology_limit("*", %TECHNOLOGY_LIMIT%)
    set_retrofit_technology_limit("*", %TECHNOLOGY_LIMIT%)
}

Fleet "roro_*" {
    set_newbuild_technology_limit("*", %TECHNOLOGY_LIMIT%)
    set_retrofit_technology_limit("*", %TECHNOLOGY_LIMIT%)
}

Fleet "tanker_*" {
    set_newbuild_technology_limit("*", %TECHNOLOGY_LIMIT%)
    set_retrofit_technology_limit("*", %TECHNOLOGY_LIMIT%)
}
