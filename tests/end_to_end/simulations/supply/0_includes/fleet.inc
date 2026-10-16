# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# One fleet of an oil and an ammonia variant of the default container vessel.
# A third of it burns ammonia from the first step, so the producer faces
# demand without waiting on fleet turnover. Decision sensitivities pinned.
# The ammonia converters emit nitrous oxide; its global warming potential is
# pinned like those in the combination model.inc.
Import Emission "nitrous_oxide"

Emission "nitrous_oxide" {
	GlobalWarmingPotential = 273        # ton CO2-eq/ton
}

Import Vessel "container_15000_teu_ice_oil"
Import Vessel "container_15000_teu_ice_ammonia"

Fleet "container_15000_teu" {
	Vessels = [
		Vessel("container_15000_teu_ice_oil"),
		Vessel("container_15000_teu_ice_ammonia")
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
}
