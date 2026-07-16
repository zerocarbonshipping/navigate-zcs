# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------- BUNKER LOGISTICS -------------------------------------
#
# This file defines the assumptions related to marine fuel supply and delivery 
# across the ports used in the example.
#
# Fossil fuel oil is treated as a liquid market fuel — widely
# available with mature infrastructure and low delivery uncertainty.
#
# For alternative fuels like FAME, supply availability and costs differ by port, 
# but no special bunkering infrastructure is assumed beyond standard marine 
# fuel handling. Cost differentials mainly reflect fuel production and regional 
# supply conditions.
#
# For fossil fuel oil there are no related transport cost, while for FAME,
# the transportation from Europe to the ports in Australia and New Zealands
# adds a cost.
#
# ----------------------------------------------------------------------------

BunkerLogistics {

	LiquidMarketFuels = [Fuel("fossil_fuel_oil")]
	
	set_distance("europe", "australia", 11000)
	set_distance("europe", "new_zealand", 12200)

	set_transport_cost("*", 0.01)
}