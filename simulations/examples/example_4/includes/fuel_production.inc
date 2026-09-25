# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUEL PRODUCTION - five fuels for four ships; both methanols feed one ship.
#
# Only the siting is set here (region and electricity source). Lead times,
# lifetimes, capacities and process economics come from the library.
# Feedstock ceilings for the two methanols are set in producer.inc.

# ---- fossil (global commodities, no production chain modelled) --------------
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"

# ---- Chilean e-methanol -----------------------------------------------------
Import Fuel "methanol_electro"
Import Plant "plant_methanol_electro_alkaline"
Plant "plant_methanol_electro_alkaline" {
    Region = Region("americas")
    Source = Source("renewable")   # dedicated wind, not the Chilean grid
}
Import Process "methanol_synthesis_electro_alkaline"
Import Process "hydrogen_electro_alkaline"
Import Process "electrolysis_stack_alkaline"
Import Feedstock "carbon_dioxide_biogenic"

# ---- Chilean e-ammonia ------------------------------------------------------
Import Fuel "ammonia_electro"
Import Plant "plant_ammonia_electro_alkaline"
Plant "plant_ammonia_electro_alkaline" {
    Region = Region("americas")
    Source = Source("renewable")
}
Import Process "ammonia_synthesis_electro_alkaline"
Import Process "nitrogen_air_separation"

# ---- European bio-methanol --------------------------------------------------
Import Fuel "methanol_bio"
Import Plant "plant_methanol_bio_gasification"
Plant "plant_methanol_bio_gasification" {
    Region = Region("europe")
    Source = Source("grid")        # a biomass plant draws from the grid
}
Import Process "methanol_synthesis_bio_gasification"
Import Feedstock "feedstock_biomethanol_gasification"

# ---- European e-fuels -------------------------------------------------------
# The same library pathways as Chile, sited in Europe. Copy, not Import: the
# Chilean nodes already carry these library names and are sited in americas.
# A second electrolyser route for e-ammonia was tried here, to give one fuel two
# competing plants under one producer. It stalls the 2038 solve, so it is left out.
Copy Plant "plant_methanol_electro_alkaline" "plant_methanol_electro_alkaline_europe"
Plant "plant_methanol_electro_alkaline_europe" {
    Region = Region("europe")
    Source = Source("renewable")
}
Copy Plant "plant_ammonia_electro_alkaline" "plant_ammonia_electro_alkaline_europe"
Plant "plant_ammonia_electro_alkaline_europe" {
    Region = Region("europe")
    Source = Source("renewable")
}

# ---- shared inputs ----------------------------------------------------------
Import Feedstock "demineralized_water"
Import Source "renewable"
Import Source "grid"
