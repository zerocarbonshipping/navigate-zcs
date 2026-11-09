# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUEL PRODUCTION - five fuels for four ships; both methanols feed one ship.
#
# The plants are regional copies of the library's pathways, named and sited the
# way DefaultPlant does it for its own copies; lead times, lifetimes, capacities
# and process economics come from the library. Loading DefaultPlant itself would
# bring in the fuels of all its other plants too.
# A second electrolyser route for e-ammonia was tried, to give one fuel two
# competing plants under one producer. It stalls the 2038 solve, so it is left
# out.

# ---- fossil (global commodities, no production chain modelled) --------------
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"

# ---- e-fuels, made in Chile or in Europe ------------------------------------
Import Fuel "methanol_electro"
Import Fuel "ammonia_electro"
Copy Plant "plant_methanol_electro_alkaline" "plant_methanol_electro_alkaline_americas"
Copy Plant "plant_ammonia_electro_alkaline"  "plant_ammonia_electro_alkaline_americas"
Copy Plant "plant_methanol_electro_alkaline" "plant_methanol_electro_alkaline_europe"
Copy Plant "plant_ammonia_electro_alkaline"  "plant_ammonia_electro_alkaline_europe"

# ---- bio-methanol, made in Europe only ---------------------------------------
Import Fuel "methanol_bio"
Copy Plant "plant_methanol_bio_gasification" "plant_methanol_bio_gasification_europe"

# ---- siting and financing, DefaultPlant's rules -------------------------------
# a biofuel plant draws from the grid
Plant "*" {
    Source = Source("grid")
}

# an e-fuel plant runs on dedicated renewable power, not the grid
Plant "*electro*" {
    Source = Source("renewable")
}

Plant "*americas" {
    Region = Region("americas")
}

Plant "*europe" {
    Region = Region("europe")
}

Plant "*electro*americas" {
    CostOfCapital = Forecast("cost_of_capital_plant_electro_americas")
}

Plant "*electro*europe" {
    CostOfCapital = Forecast("cost_of_capital_plant_electro_europe")
}

Plant "*bio*europe" {
    CostOfCapital = Forecast("cost_of_capital_plant_bio_europe")
}
