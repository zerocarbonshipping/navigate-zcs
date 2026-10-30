# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FUEL PRODUCTION - fuel oil and LNG (market fuels), FAME, e-diesel and
# e-methanol, all made in Europe with the library's plants. Region, Source and
# CostOfCapital are set here as DefaultPlant does (Import/Copy brings none).

# ---- fossil (market fuels, no production chain) -----------------------------
Import Fuel "fossil_fuel_oil"
Import Fuel "liquefied_natural_gas"

# ---- fuels named by the copied regulation but not used by this case ---------
# (imported only so that Regulation "co2_price_germany" parses)
Import Fuel "methanol_bio"
Import Fuel "methane_bio"
Import Fuel "methane_electro"
Import Fuel "ammonia_blue"
Import Fuel "ammonia_electro"

# ---- FAME from used cooking oil ---------------------------------------------
Import Fuel "fatty_acid_methyl_ester"
Import Process "fatty_acid_methyl_ester_synthesis"
Import Feedstock "used_cooking_oil"
Import Feedstock "methanol_grey"
Copy Plant "plant_fatty_acid_methyl_ester" "plant_fatty_acid_methyl_ester_europe"
Plant "plant_fatty_acid_methyl_ester_europe" {
	Region = Region("europe")
	Source = Source("grid")
	CostOfCapital = Forecast("cost_of_capital_plant_bio_europe")
}

# ---- e-diesel ---------------------------------------------------------------
Import Fuel "diesel_electro"
Import Process "diesel_synthesis_electro_alkaline"
Copy Plant "plant_diesel_electro_alkaline" "plant_diesel_electro_alkaline_europe"
Plant "plant_diesel_electro_alkaline_europe" {
	Region = Region("europe")
	Source = Source("renewable")
	CostOfCapital = Forecast("cost_of_capital_plant_electro_europe")
}

# ---- e-methanol -------------------------------------------------------------
Import Fuel "methanol_electro"
Import Process "methanol_synthesis_electro_alkaline"
Copy Plant "plant_methanol_electro_alkaline" "plant_methanol_electro_alkaline_europe"
Plant "plant_methanol_electro_alkaline_europe" {
	Region = Region("europe")
	Source = Source("renewable")
	CostOfCapital = Forecast("cost_of_capital_plant_electro_europe")
}

# ---- shared inputs ----------------------------------------------------------
Import Process "hydrogen_electro_alkaline"
Import Process "electrolysis_stack_alkaline"
Import Feedstock "carbon_dioxide_biogenic"
Import Feedstock "demineralized_water"
Import Source "renewable"
Import Source "grid"
