# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ REGULAR FLEET --------------------------------
#
# This file defines the baseline Baltic tanker fleet without any additional
# energy-efficiency measures. The fleet includes both coastal tankers (~7,500
# DWT) and MR tankers (~47,000 DWT), operating between Helsinki, Stockholm,
# Tallinn, and Gdansk. 
#
# Vessels can be modeled on conventional fossil fuels or on e-ammonia,
# allowing direct comparison of fuel transition costs and emissions. In this
# baseline version, no efficiency upgrades are applied, providing a reference
# case against which the EE fleet can be compared.
#
# -----------------------------------------------------------------------------

Copy Vessel "tanker_47k_dwt_ice_oil"        "mid_range_regular_oil"
Copy Vessel "tanker_47k_dwt_ice_ammonia"    "mid_range_regular_ammonia"

Copy Vessel "tanker_7500_dwt_ice_oil"        "coastal_regular_oil"
Copy Vessel "tanker_7500_dwt_ice_ammonia"    "coastal_regular_ammonia"

Fleet "mid_range_regular" {
	Vessels = [Vessel("mid_range_regular_oil"), Vessel("mid_range_regular_ammonia")]

	InitialVessels = 2
	InitialSplit = [0.5, 0.5]

	InitialAgeDistribution = [
		Curve("age_dist_mid_range_regular_oil"),
		Curve("age_dist_mid_range_regular_ammonia")
	]


	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant. 
	TradeGrowth = 0.05

	# disallow the approximation of technology uptake from other fleets
	AllowTechnologyApproximation = FALSE
}

Fleet "coastal_regular" {
	Vessels = [Vessel("coastal_regular_oil"), Vessel("coastal_regular_ammonia")]

	InitialVessels = 3
	InitialSplit = [1.0, 0.0]

	InitialAgeDistribution = [
		Curve("age_dist_coastal_regular_oil"),
		0
	]

	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant.
	TradeGrowth = 0.05

	# disallow the approximation of technology uptake from other fleets
	AllowTechnologyApproximation = FALSE
}