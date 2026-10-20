# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fuel "methanol_bio" {
	FuelType = METHANOL

	LowerHeatingValue = Variable("lower_heating_value_methanol")
	MassDensity = Variable("mass_density_methanol")
	
	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_methanol"))
}
