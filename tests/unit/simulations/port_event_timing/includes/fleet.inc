# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A single oil vessel type. Its decision calibration is pinned so the deck is
# not re-sized by upstream calibration changes; the fuel choice under test
# does not depend on it.
Import Vessel "container_15000_teu_ice_oil"

Fleet "container_15000_teu" {
	Vessels = [Vessel("container_15000_teu_ice_oil")]

	InitialVessels = 100
	InitialSplit = [1.0]
	InitialAgeDistribution = [Curve("age_dist_container_15000_teu_oil")]

	Inertia = 0.0
	InterFuelSensitivity = 0.75
	IntraFuelSensitivity = 0.75
	FuelConversionSensitivity = 2
	TechnologySensitivity = 2
}
