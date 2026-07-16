# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------- EE FLEET ------------------------------------
#
# This file defines the Baltic tanker fleet with energy-efficiency measures
# enabled. As with the regular fleet, it includes both coastal tankers (~7,500
# DWT) and MR tankers (~47,000 DWT), trading between Helsinki, Stockholm,
# Tallinn, and Gdansk.
#
# Vessels can operate on fossil fuels or adopt e-ammonia, and have
# similar specifications to those in the regular fleet. 
#
# This efficient fleet, however, get energy efficiency measures enabled from the
# .inc file "energy_efficiencies".
#
# -----------------------------------------------------------------------------

Copy Vessel "tanker_47k_dwt_ice_oil"        "mid_range_efficient_oil"
Copy Vessel "tanker_47k_dwt_ice_ammonia"    "mid_range_efficient_ammonia"

Copy Vessel "tanker_7500_dwt_ice_oil"        "coastal_efficient_oil"
Copy Vessel "tanker_7500_dwt_ice_ammonia"    "coastal_efficient_ammonia"


Fleet "mid_range_efficient" {
	Vessels = [Vessel("mid_range_efficient_oil"), Vessel("mid_range_efficient_ammonia")]

	InitialVessels = 2
	InitialSplit = [0.5, 0.5]

	InitialAgeDistribution = [
		Curve("age_dist_mid_range_efficient_oil"),
		Curve("age_dist_mid_range_efficient_ammonia")
	]


	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant. 
	TradeGrowth = 0.05
}

Fleet "coastal_efficient" {
	Vessels = [Vessel("coastal_efficient_oil"), Vessel("coastal_efficient_ammonia")]

	InitialVessels = 3
	InitialSplit = [1.0, 0.0]

	InitialAgeDistribution = [
		Curve("age_dist_coastal_efficient_oil"),
		0
	]

	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant.
	TradeGrowth = 0.05
}

Fleet "*_efficient" {
	Technologies = [
		Technology("air_lubrication_tanker_35k_dwt"),
		Technology("cargo_systems_tanker_35k_dwt"),
		Technology("exhaust_gas_boiler_ae_tanker_35k_dwt"),
		Technology("flettner_rotor_tanker_35k_dwt"),
		Technology("hull_painting_tanker_35k_dwt"),
		Technology("lighting_system_tanker_35k_dwt"),
		Technology("propeller_improvement_devices_tanker_35k_dwt"),
		Technology("variable_frequency_drive_tanker_35k_dwt")
	]
}
