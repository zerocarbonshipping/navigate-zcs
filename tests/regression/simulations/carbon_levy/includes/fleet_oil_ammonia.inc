# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# A single fleet with only the oil and ammonia variants of the default
# container vessel: the levy must steer choices toward exactly one
# alternative fuel. No conversion lane and no speed management — the levy's
# effect on bunkering and newbuild choice is the only mechanism in play.
# Decision sensitivities come from the shared pinned calibration
# (0_includes/fleet_calibration.inc), included after this file in the .nav.
Import Vessel "container_15000_teu_ice_oil"
Import Vessel "container_15000_teu_ice_ammonia"

Fleet "container_15000_teu" {
	Vessels = [
		Vessel("container_15000_teu_ice_ammonia"),
		Vessel("container_15000_teu_ice_oil")
	]

	InitialVessels = Variable("initial_vessels_container_15000_teu")

	# a substantial ammonia-capable share from the start, so levy-priced
	# ammonia demand exists at scale before the fleet turns over
	InitialSplit = [
		0.300,
		0.700
	]

	InitialAgeDistribution = [
		Curve("age_dist_container_15000_teu_oil"),
		Curve("age_dist_container_15000_teu_oil")
	]
}
