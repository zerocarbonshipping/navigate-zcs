# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Fuels and Emissions
#
# Attributes covered:
#   Fuel:     FuelType, LowerHeatingValue, MassDensity
#   Emission: GlobalWarmingPotential, FuelType
#
# Commands covered:
#   Fuel: set_ttw

Fuel "hfo" {
	FuelType = OIL
	LowerHeatingValue = 41.2
	MassDensity = 0.9
	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}

Fuel "lng" {
	FuelType = METHANE
	LowerHeatingValue = 50.0
	MassDensity = 0.43
	set_ttw("carbon_dioxide", 2.75)
	set_ttw("methane", 0.06)
	set_ttw("nitrous_oxide", 0.00015)
}

Fuel "bio_methanol" {
	FuelType = METHANOL
	LowerHeatingValue = 19.9
	MassDensity = 0.791
	set_ttw("carbon_dioxide", 1.38)
}

Fuel "blue_ammonia" {
	FuelType = AMMONIA
	LowerHeatingValue = 18.8
	MassDensity = 0.623
	set_ttw("carbon_dioxide", 0)
	set_ttw("nitrous_oxide", 0.001)
}

Emission "carbon_dioxide" {
	GlobalWarmingPotential = 1
}

Emission "methane" {
	GlobalWarmingPotential = 25
	FuelType = METHANE
}

Emission "nitrous_oxide" {
	GlobalWarmingPotential = 273
}
