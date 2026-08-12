# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# A single fleet with only the oil and ammonia variants of the default
# container vessel: the regulation must pull demand toward exactly one
# alternative fuel, so the supply constraint on that fuel is the only
# mechanism in play. Decision sensitivities come from Load DefaultCalibration
# in the .nav.
Import Vessel "container_15000_teu_ice_oil"
Import Vessel "container_15000_teu_ice_ammonia"

Fleet "container_15000_teu" {
	Vessels = [
		Vessel("container_15000_teu_ice_ammonia"),
		Vessel("container_15000_teu_ice_oil")
	]

	InitialVessels = Variable("initial_vessels_container_15000_teu")

	# a substantial ammonia-capable share from the start: the deck tests the
	# demand signal propagating from the bunker algorithm to the producer,
	# not the speed of fleet turnover, so ammonia demand must exist at scale
	# from the first step
	InitialSplit = [
		0.300,
		0.700
	]

	InitialAgeDistribution = [
		Curve("age_dist_container_15000_teu_oil"),
		Curve("age_dist_container_15000_teu_oil")
	]

	set_fuel_conversion_cost("*ice_oil*", "*ice_ammonia*", 36.5e6)

	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.5
}
