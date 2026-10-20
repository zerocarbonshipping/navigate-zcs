# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fuel "methane_electro" {
	FuelType = METHANE

	LowerHeatingValue = Variable("lower_heating_value_methane")
	MassDensity = Variable("mass_density_methane")
	
	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_methane"))
}
