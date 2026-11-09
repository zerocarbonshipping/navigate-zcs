# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# REGIONS - where fuels get made, and the economics of making them.
# All cost curves are referenced by name from the assumptions library.
#
# The methanol synthesis steps carry negative CO2 terms: the molecule locks up
# captured carbon, so production is a WTT sink and combustion releases it again.

Region "americas" {
    set_source_opex("renewable", Forecast("electricity_cost_americas_mid"))
    set_source_opex("grid", Forecast("electricity_cost_americas_mid"))
    set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_americas"))
}

Region "europe" {
    set_source_opex("renewable", Forecast("electricity_cost_europe_mid"))
    set_source_opex("grid", Forecast("electricity_cost_europe_mid"))
    set_source_wtt("grid", "carbon_dioxide", Forecast("grid_emissions_europe"))
}

# Production economics that do not vary by region, so a plant can be sited
# anywhere.
Region "*" {

    # ---- feedstocks ----
    set_feedstock_cost("demineralized_water", Forecast("demineralized_water_cost"))
    set_feedstock_cost("carbon_dioxide_biogenic", Forecast("carbon_dioxide_biogenic_cost"))
    set_feedstock_cost("feedstock_biomethanol_gasification", Forecast("feedstock_biomethanol_gasification_cost"))
    set_feedstock_wtt("carbon_dioxide_biogenic", "carbon_dioxide", Forecast("carbon_dioxide_biogenic_capture_rate"))

    # ---- hydrogen, shared by both e-fuels ----
    # Timetable rather than Forecast: cost depends on year and on plant size.
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

    # ---- e-methanol: hydrogen + biogenic CO2 ----
    set_process_capex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_capex"))
    set_process_opex("methanol_synthesis_electro_*", Timetable("methanol_synthesis_electro_opex"))
    set_process_energy("methanol_synthesis_electro_*", Forecast("methanol_synthesis_electro_energy"))
    set_process_wtt("methanol_synthesis_electro_*", "carbon_dioxide",
                    <Variable("methanol_carbon_dioxide_conversion") - Variable("carbon_dioxide_per_methanol")>)

    # ---- e-ammonia: hydrogen + nitrogen from air ----
    set_process_capex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_capex"))
    set_process_opex("ammonia_synthesis_electro_*", Timetable("ammonia_synthesis_opex"))
    set_process_energy("ammonia_synthesis_electro_*", Forecast("ammonia_synthesis_energy"))

    # ---- bio-methanol: gasified biomass ----
    set_process_capex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_capex"))
    set_process_opex("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_opex"))
    set_process_energy("methanol_synthesis_bio_gasification", Forecast("methanol_synthesis_bio_gasification_energy"))
    set_process_wtt("methanol_synthesis_bio_gasification", "carbon_dioxide", <-Variable("carbon_dioxide_per_methanol")>)

    # ---- plant to quayside within a region ----
    set_transport_cost("truck", 0.0)
    set_transport_wtt("truck", "carbon_dioxide", Forecast("truck_emissions"))
}

# A command taking a node name as a string key needs that node to exist already,
# so this is imported rather than auto-resolved like a Fuel() reference.
Import Transport "truck"
