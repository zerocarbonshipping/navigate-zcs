# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ---------------------- BUNKER LOGISTICS -------------------------------------
#
# This file defines the assumptions related to marine fuel supply and delivery 
# across the ports used in the scenario.
#
# In this case, fossil fuel oil is treated as a liquid market fuel —
# widely available, with mature infrastructure and low delivery uncertainty.
#
# ----------------------------------------------------------------------------

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil")]

	set_distance("*", "*", 1000)
	set_transport_cost("*", 0.1)
}
