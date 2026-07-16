# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fuel "liquefied_natural_gas" {
	FuelType = METHANE

	LowerHeatingValue = Variable("lower_heating_value_natural_gas")
	MassDensity = Variable("mass_density_liquefied_natural_gas")
	
	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_natural_gas"))
}