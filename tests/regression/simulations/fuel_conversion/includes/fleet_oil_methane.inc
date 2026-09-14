# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# An oil-dominated fleet with a methane variant reachable only through fuel
# conversion (methane newbuilds are disabled below). Decision sensitivities
# come from the shared pinned calibration (0_includes/fleet_calibration.inc),
# included after this file in the .nav.
Import Vessel "container_15000_teu_ice_oil"
Import Vessel "container_15000_teu_ice_methane"

# Pinned discounting inputs, overriding the imported defaults: the conversion
# NPV discounts fuel savings at the destination's CostOfCapital, and the
# levelization window is the destination's remaining lifetime — a zero rate or
# equal lifetimes would make the baseline blind to discounting and
# operating-window changes (the activation guards assert both stay pinned).
Vessel "container_15000_teu_ice_oil" {
	Lifetime = 25
	CostOfCapital = 0.08
}

Vessel "container_15000_teu_ice_methane" {
	Lifetime = 30
	CostOfCapital = 0.08
}

Fleet "container_15000_teu" {
	Vessels = [
		Vessel("container_15000_teu_ice_oil"),
		Vessel("container_15000_teu_ice_methane")
	]

	InitialVessels = Variable("initial_vessels_container_15000_teu")

	# almost all-oil at the start: methane uptake in the results is then
	# driven by the conversion mechanism, not the initial composition
	InitialSplit = [
		0.900,
		0.100
	]

	InitialAgeDistribution = [
		Curve("age_dist_container_15000_teu_oil"),
		Curve("age_dist_container_15000_teu_oil")
	]

	# with the spread age distribution, a five-year cycle makes some cohort
	# eligible at every yearly step
	RetrofitFrequency = 5
	FuelConversionMinimumAge = 5

	set_fuel_conversion_cost("*ice_oil*", "*ice_methane*", 10e6)

	# conversion is the only oil -> methane channel
	set_newbuild_available("container_15000_teu_ice_methane", FALSE)
}
