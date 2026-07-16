# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------ FLEET ---------------------------------------
#
# This file defines the bulk carrier fleet used in the Pacific regional scenario. 
# The fleet consists of Handysize vessels trading between Australia,
# New Zealand, and small island ports (Fiji, Samoa, Tonga).
#
# For simplicity, vessel specifications (capacity, load levels, capital and 
# operating costs) are assumed to be the same regardless of whether they run 
# on fuel oil or FAME. Differences in fuel type, emissions, and costs are captured
# through the fuel production, bunker logistics and regulation definition
#
# The vessels are of different ages, and you can change the initital number, the
# level of trade growth or allowance of speed management to see how it affects
# the output.
#
# ----------------------------------------------------------------------------- 

Copy Vessel "bulk_carrier_26k_dwt_ice_oil" "bulk_carrier_handysize_oil"

Fleet "bulk_carrier_handysize" {
	# vessel types
	Vessels = [Vessel("bulk_carrier_handysize_oil")]

	# initial conditions
	InitialVessels = 6

	InitialSplit = [1.]

	InitialAgeDistribution = [
		Curve("age_dist_bulk_carrier_handysize_oil")
	]


	# Trade growth: annual growth rate of 5%, but can be changed if expected otherwise or disabled to keep constant. 
	TradeGrowth = 0.05

	# Speed management: enabled to allow adjustments in operational behavior
	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.5
}