# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fuel "fossil_fuel_oil" {
	FuelType = OIL
	LiquidMarket = TRUE

	LowerHeatingValue = Variable("lower_heating_value_oil")
	MassDensity = Variable("mass_density_oil")
	
	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_oil"))
}
