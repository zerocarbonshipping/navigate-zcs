# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of fuels


# Definition of "heavy_fuel_oil"
Fuel "heavy_fuel_oil" {
	FuelType = OIL

	LowerHeatingValue = 41.2
	MassDensity = 0.9
	
	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}


# Definition of "methane_electro" 
Fuel "methane_electro" {
	FuelType = METHANE

	LowerHeatingValue = 50.0
	MassDensity = 0.43
	
	set_ttw("carbon_dioxide", 2.75)
}

# Definition of "methanol_bio" 
Fuel "methanol_bio" {
	FuelType = METHANOL

	LowerHeatingValue = 19.9
	MassDensity = 0.791
	
	set_ttw("carbon_dioxide", 1.38)
}

# Definition of "ammonia_blue" 
Fuel "ammonia_blue" {
	FuelType = AMMONIA

	LowerHeatingValue = 18.8
	MassDensity = 0.623
}
