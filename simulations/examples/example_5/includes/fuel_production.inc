# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUEL PRODUCTION - fossil fuels as traded commodities; the new fuels made either
# in Trinidad, on the US Gulf Coast ("americas") or in Chile, and shipped in.
# The Gulf Coast makes all four; Trinidad all but bio-methanol; Chile the two
# e-fuels. Which wins at each port is
# left to cost and delivery distance (bunker_logistics.inc).
#
# Only siting and financing are set here. Import Plant does not bring the cost of
# capital (the library sets it in DefaultPlant), so each plant states its own.
# Capacities, lead times, lifetimes and process economics come from the library.

# ---- fossil (global commodities, no production chain modelled) --------------
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"

# ---- Trinidad blue ammonia: natural gas reforming with carbon capture --------
Import Fuel "ammonia_blue"
Import Plant "plant_ammonia_blue"
Plant "plant_ammonia_blue" {
    Region = Region("caribbean")
    Source = Source("grid")
    CostOfCapital = Forecast("cost_of_capital_plant_blue_americas")
}
Import Process "ammonia_synthesis_blue"
Import Process "autothermal_reforming"
Import Process "nitrogen_air_separation"
Import Feedstock "natural_gas"

# ---- Trinidad e-ammonia: electrolysis on dedicated renewables ----------------
Import Fuel "ammonia_electro"
Import Plant "plant_ammonia_electro_alkaline"
Plant "plant_ammonia_electro_alkaline" {
    Region = Region("caribbean")
    Source = Source("renewable")
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}
Import Process "ammonia_synthesis_electro_alkaline"
Import Process "hydrogen_electro_alkaline"
Import Process "electrolysis_stack_alkaline"

# ---- Trinidad e-methanol: hydrogen and biogenic CO2 --------------------------
Import Fuel "methanol_electro"
Import Plant "plant_methanol_electro_alkaline"
Plant "plant_methanol_electro_alkaline" {
    Region = Region("caribbean")
    Source = Source("renewable")
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}
Import Process "methanol_synthesis_electro_alkaline"
Import Feedstock "carbon_dioxide_biogenic"

# ---- bio-methanol from the US Gulf Coast, shipped in ------------------
Import Fuel "methanol_bio"
Import Plant "plant_methanol_bio_gasification"
Plant "plant_methanol_bio_gasification" {
    Region = Region("americas")
    Source = Source("grid")
    CostOfCapital = Forecast("cost_of_capital_plant_bio_americas")
}
Import Process "methanol_synthesis_bio_gasification"
Import Feedstock "feedstock_biomethanol_gasification"

# ---- the same three pathways on the US Gulf Coast, shipped in ---------------
# Copy, not Import: the Trinidad plants already carry the library names.
Copy Plant "plant_ammonia_blue" "plant_ammonia_blue_americas"
Plant "plant_ammonia_blue_americas" {
    Region = Region("americas")
    Source = Source("grid")
    CostOfCapital = Forecast("cost_of_capital_plant_blue_americas")
}
Copy Plant "plant_ammonia_electro_alkaline" "plant_ammonia_electro_alkaline_americas"
Plant "plant_ammonia_electro_alkaline_americas" {
    Region = Region("americas")
    Source = Source("renewable")
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}
Copy Plant "plant_methanol_electro_alkaline" "plant_methanol_electro_alkaline_americas"
Plant "plant_methanol_electro_alkaline_americas" {
    Region = Region("americas")
    Source = Source("renewable")
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}

# ---- Chilean e-fuels: cheap wind, far away, shipped in through Panama --------
Copy Plant "plant_ammonia_electro_alkaline" "plant_ammonia_electro_alkaline_chile"
Plant "plant_ammonia_electro_alkaline_chile" {
    Region = Region("chile")
    Source = Source("renewable")
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}
Copy Plant "plant_methanol_electro_alkaline" "plant_methanol_electro_alkaline_chile"
Plant "plant_methanol_electro_alkaline_chile" {
    Region = Region("chile")
    Source = Source("renewable")
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}

# ---- shared inputs ----------------------------------------------------------
Import Feedstock "demineralized_water"
Import Source "renewable"
Import Source "grid"

# ---- fuels named by the library's EU regulations, never bunkered here --------
Import Fuel "fatty_acid_methyl_ester"
Import Fuel "diesel_electro"
Import Fuel "methane_bio"
Import Fuel "methane_electro"
