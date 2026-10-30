# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# REGIONS - where fuels get made, and what making them costs.
#
# "caribbean" is new to this deck: Trinidad's gas and its industrial estate at
# Point Lisas. "americas" is the library's region, used for bio-methanol only.

Region "caribbean" {
    # INVENTED proxy: the library's Americas renewable cost. The one Caribbean
    # figure found is dated: Jamaica's solar contracts at about 85 USD/MWh (2016-17).
    set_source_opex("renewable", Forecast("electricity_cost_americas_mid"))

    # Trinidad's gas-fired grid
    set_source_opex("grid", Forecast("electricity_cost_trinidad_grid"))
    set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_trinidad"))

    # The library's global gas price. Trinidad's gas is short: Nutrien closed at
    # Point Lisas in October 2025 and three of Proman's five methanol plants are down.
    set_feedstock_cost("natural_gas", Forecast("natural_gas_price_global"))
}

# Trinidad & Tobago residential tariff, June 2025, gas-subsidised: 0.062 USD/kWh
# (GlobalPetrolPrices). INVENTED: held flat.
Forecast "electricity_cost_trinidad_grid" {
    Table = [
        "01-01-2025"    62
        "01-01-2050"    62
    ]
    Extrapolate = FLAT
}

# Trinidad & Tobago lifecycle grid intensity, 2024: 682 gCO2e/kWh (Ember via Our
# World in Data). INVENTED: held flat.
Forecast "grid_emissions_trinidad" {
    Table = [
        "01-01-2025"    0.682
        "01-01-2050"    0.682
    ]
    Extrapolate = FLAT
}

# Chile's Magallanes region, the wind resource example_4 builds on. INVENTED
# proxy: the library has no Chile-specific cost, so the library's Americas LOW
# case stands for its wind (49 USD/MWh in 2026, 33 by 2050, against the mid
# case's 62 and 41 used for Trinidad and the Gulf Coast).
Region "chile" {
    set_source_opex("renewable", Forecast("electricity_cost_americas_low"))
    set_source_opex("grid", Forecast("electricity_cost_americas_low"))
    set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_americas"))
}

Region "americas" {
    set_source_opex("renewable", Forecast("electricity_cost_americas_mid"))
    set_source_opex("grid", Forecast("electricity_cost_americas_mid"))
    set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_americas"))
}

# Production economics that do not depend on the site, from the library's
# DefaultRegion.
Region "*" {

    # ---- feedstocks ----
    set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))
    set_feedstock_cost("carbon_dioxide_biogenic", Forecast("carbon_dioxide_biogenic_cost"))
    set_feedstock_cost("feedstock_biomethanol_gasification", Forecast("feedstock_biomethanol_gasification_cost"))
    set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", Forecast("carbon_dioxide_biogenic_capture_rate"))
    set_feedstock_wtt("natural_gas", "carbon_dioxide", Forecast("natural_gas_wtt_carbon_dioxide"))
    set_feedstock_wtt("natural_gas", "methane", Forecast("natural_gas_wtt_methane"))

    # ---- blue hydrogen: autothermal reforming, captured CO2 stored ----
    set_process_capex("autothermal_reforming", Timetable("autothermal_reforming_capex"))
    set_process_opex("autothermal_reforming", <Timetable("autothermal_reforming_opex") + Forecast("carbon_transport_storage_cost") * Forecast("autothermal_reforming_capture_rate") * Variable("carbon_dioxide_per_hydrogen_blue")>)
    set_process_energy("autothermal_reforming", Forecast("autothermal_reforming_energy"))
    set_process_wtt("autothermal_reforming", "carbon_dioxide", <(1. - Forecast("autothermal_reforming_capture_rate")) * Variable("carbon_dioxide_per_hydrogen_blue")>)

    # ---- e-hydrogen: alkaline electrolysis ----
    set_process_capex("electrolysis_stack_alkaline", Timetable("electrolysis_stack_alkaline_capex"))
    set_process_opex("electrolysis_stack_alkaline", Timetable("electrolysis_stack_alkaline_opex"))
    set_process_energy("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_energy"))
    set_process_lifetime("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_lifetime"))
    set_process_replacement("electrolysis_stack_alkaline", Forecast("electrolysis_stack_alkaline_replacement"))

    set_process_capex("hydrogen_electro_alkaline", Timetable("hydrogen_electro_alkaline_capex"))
    set_process_opex("hydrogen_electro_alkaline", Timetable("hydrogen_electro_alkaline_opex"))
    set_process_energy("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_energy"))
    set_process_lifetime("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_lifetime"))
    set_process_replacement("hydrogen_electro_alkaline", Forecast("hydrogen_electro_alkaline_replacement"))

    # ---- ammonia, blue and electro ----
    set_process_capex("ammonia_synthesis_*", Timetable("ammonia_synthesis_capex"))
    set_process_opex("ammonia_synthesis_*", Timetable("ammonia_synthesis_opex"))
    set_process_energy("ammonia_synthesis_*", Forecast("ammonia_synthesis_energy"))

    # ---- e-methanol: hydrogen + biogenic CO2 ----
    set_process_capex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_capex"))
    set_process_opex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_opex"))
    set_process_energy("methanol_synthesis_electro_*", Forecast("methanol_synthesis_electro_energy"))
    set_process_wtt("methanol_synthesis_electro_*", "carbon_dioxide",
                    <Variable("methanol_carbon_dioxide_conversion") - Variable("carbon_dioxide_per_methanol")>)

    # ---- bio-methanol: gasified biomass ----
    set_process_capex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_capex"))
    set_process_opex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_opex"))
    set_process_energy("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_energy"))
    set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", <-Variable("carbon_dioxide_per_methanol")>)

    # ---- plant to quayside within a region ----
    set_transport_cost("truck", 0.0)
    set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))
}

# A command taking a node name as a string key needs that node to exist already.
Import Transport "truck"
