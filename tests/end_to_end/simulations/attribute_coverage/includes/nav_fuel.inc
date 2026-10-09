# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Fuels and Emissions
#
# Attributes covered:
#   Fuel:     FuelType, LiquidMarket, LowerHeatingValue, MassDensity
#   Emission: GlobalWarmingPotential, FuelType
#
# Commands covered:
#   Fuel: set_ttw
#
# IDs covered:
#   FuelType: every FuelTypeID, one fuel each

Fuel "hfo" {
	FuelType = OIL
	LiquidMarket = TRUE
	LowerHeatingValue = 41.2
	MassDensity = 0.9
	set_ttw("carbon_dioxide", 3.114)
	set_ttw("methane", 0.00005)
	set_ttw("nitrous_oxide", 0.00018)
}

Fuel "lng" {
	FuelType = METHANE
	LiquidMarket = TRUE
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
	LiquidMarket = TRUE
	LowerHeatingValue = 18.8
	MassDensity = 0.623
	set_ttw("carbon_dioxide", 0)
	set_ttw("nitrous_oxide", 0.001)
}

# One liquid-market fuel per remaining FuelType, so every FuelTypeID is written.
# No vessel can burn them; they are bunkered at priced ports only.

Fuel "ethanol" {
	FuelType = ETHANOL
	LiquidMarket = TRUE
	LowerHeatingValue = 26.8
	MassDensity = 0.789
	set_ttw("carbon_dioxide", 1.91)
}

Fuel "hydrogen" {
	FuelType = HYDROGEN
	LiquidMarket = TRUE
	LowerHeatingValue = 120.0
	MassDensity = 0.071
	set_ttw("carbon_dioxide", 0)
}

Fuel "lpg" {
	FuelType = LPG
	LiquidMarket = TRUE
	LowerHeatingValue = 46.0
	MassDensity = 0.54
	set_ttw("carbon_dioxide", 3.0)
}

Fuel "electricity" {
	FuelType = ELECTRICITY
	LiquidMarket = TRUE
	LowerHeatingValue = 3.6
	MassDensity = 1
	set_ttw("carbon_dioxide", 0)
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
