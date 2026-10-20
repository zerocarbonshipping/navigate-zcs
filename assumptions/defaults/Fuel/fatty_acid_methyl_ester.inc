# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Fuel "fatty_acid_methyl_ester" {
	FuelType = OIL

	LowerHeatingValue = Variable("lower_heating_value_fame")
	MassDensity = Variable("mass_density_fame")

	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_fame"))
}
