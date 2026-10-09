# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# One fleet of an oil and a methane variant of the default container vessel,
# so a policy has a fuel to shift between and the two variants face different
# fuel costs. Decision sensitivities and the vessels' economics are pinned.
Import Vessel "container_15000_teu_ice_oil"
Import Vessel "container_15000_teu_ice_methane"

Vessel "container_15000_teu_ice_oil" {
	Lifetime = 25
	CostOfCapital = 0.08
}

Vessel "container_15000_teu_ice_methane" {
	Lifetime = 30
	CostOfCapital = 0.08
}

# One methane slip on both methane converters, so the slip a policy averages
# over them does not depend on their capacities or efficiencies.
Import Converter "propulsion_ice_methane_container_15000_teu"
Import Converter "electrical_ice_methane_container_15000_teu"

Converter "propulsion_ice_methane_container_15000_teu" {
	set_slip_fraction(METHANE, 0.01)
}

Converter "electrical_ice_methane_container_15000_teu" {
	set_slip_fraction(METHANE, 0.01)
}

Fleet "container_15000_teu" {
	Vessels = [
		Vessel("container_15000_teu_ice_oil"),
		Vessel("container_15000_teu_ice_methane")
	]

	InitialVessels = 500

	InitialSplit = [
		0.700,
		0.300
	]

	InitialAgeDistribution = [
		Curve("age_dist_container_15000_teu_oil"),
		Curve("age_dist_container_15000_teu_oil")
	]

	Inertia = 0.0
	InterFuelSensitivity = 0.75
	IntraFuelSensitivity = 0.75
	TechnologySensitivity = 2

	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.5
}
