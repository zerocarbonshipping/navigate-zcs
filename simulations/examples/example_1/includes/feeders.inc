# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# -------------------------------- FEEDER FLEET ---------------------------------------
#
# This file defines the feeder fleet used in the example, with vessels representing
# the regional distribution layer of the transport network.
# 
# Operating from Rotterdam to ports like Hamburg and Aalborg, they must navigate both
# infrastructure limitations and stricter European regulations. Their smaller size and
# operational context reflect the challenges and opportunities of short-sea shipping.
#
# -------------------------------------------------------------------------------------

Copy Vessel "container_1500_teu_ice_oil"        "feeder_oil"
Copy Vessel "container_1500_teu_ice_methanol"   "feeder_methanol"

Fleet "feeders" {
	# Vessel types
	Vessels = [Vessel("feeder_oil"),
			   Vessel("feeder_methanol")]

	# Initial conditions - i.e. how many vessels of which type and age
	InitialVessels = 50

	InitialSplit = [0.96,
                	0.04]

	InitialAgeDistribution = [
		Curve("age_dist_feeders_oil"),
		Curve("age_dist_feeders_methanol")
	]


	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant. 
	# TradeGrowth = 0.05

	# Fuel conversion cost: defined for future retrofit from oil to methanol
	set_fuel_conversion_cost("feeder_oil", "feeder_methanol", 10.3e6)

	# Speed management: enabled to allow adjustments in operational behavior
    AllowSpeedManagement = FALSE # or TRUE
	MaximumSpeedChange = 0.5
}