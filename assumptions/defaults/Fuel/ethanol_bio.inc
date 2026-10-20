# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# TODO: Change FuelType from METHANOL to ETHANOL when vessel types support ethanol.
# Currently using METHANOL so ethanol can reuse existing methanol vessel/converter infrastructure.

Fuel "ethanol_bio" {
	FuelType = METHANOL

	LowerHeatingValue = Variable("lower_heating_value_ethanol")
	MassDensity = Variable("mass_density_ethanol")

	set_ttw("carbon_dioxide", Variable("carbon_dioxide_per_ethanol"))
}
