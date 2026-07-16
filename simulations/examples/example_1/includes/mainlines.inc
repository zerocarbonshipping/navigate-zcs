# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------------- CONTAINER FLEET --------------------------------------
#
# This file defines the mainline container fleet used in the scenario, which operates 
# along the long-haul route between Singapore and Rotterdam — a key global trade corridor.
#
# The fleet begins with a number of oil-fueled vessel nearing the end of their operational life
# creating a decision point: should the company reinvest in traditional fossil ships or 
# transition to methanol as a low-emission alternative?
#
# This setup enables analysis of fuel transition timing, cost impacts, and emissions 
# trade-offs across the life cycle of long-haul container shipping.
#
# ----------------------------------------------------------------------------------

Copy Vessel "container_15000_teu_ice_oil" "mainline_oil"
Copy Vessel "container_15000_teu_ice_methanol" "mainline_methanol"

Fleet "mainlines" {
	# Vessel types
	Vessels = [Vessel("mainline_oil"),
			   Vessel("mainline_methanol")]

	# Initial conditions - i.e. how many vessels of which type and age
	InitialVessels = 5

	InitialSplit = [0.800,
                    0.200]

	InitialAgeDistribution = [
		Curve("age_dist_mainlines_oil"),
		Curve("age_dist_mainlines_methanol")
	]


	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant. 
	# TradeGrowth = 0.05
	
	# Fuel conversion cost: defined for future retrofit from oil to methanol
	set_fuel_conversion_cost("mainline_oil", "mainline_methanol", 24.3e6)

	# Speed management: enabled to allow adjustments in operational behavior
	AllowSpeedManagement = TRUE # or TRUE
	MaximumSpeedChange = 0.5
}
