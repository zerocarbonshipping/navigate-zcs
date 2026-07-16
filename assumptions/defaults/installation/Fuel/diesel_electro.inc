# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fuel "diesel_electro" {
	FuelType = OIL

	LowerHeatingValue = Variable("lower_heating_value_diesel")
	MassDensity = Variable("mass_density_diesel")
	
	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_diesel_electro"))
}
