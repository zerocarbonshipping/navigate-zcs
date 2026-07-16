# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# --------------------- BUNKER LOGISTICS -------------------------------------
#
# This file defines the cost assumptions related to transporting fuel from a
# given production region to a bunker hub (port).
#
# In this case, fossil fuel oil is treated as a liquid market fuel —
# widely available, with mature infrastructure and low delivery uncertainty.
# For alternative fuels like bio-methanol, the cost and complexity of bunkering 
# can vary significantly depending on the port and supporting infrastructure.
#
# To keep the model streamlined and educational, fuel transport distances 
# and costs have been generalized, reflecting typical conditions 
# rather than port-specific variations.
#
# These parameters influence the total cost of fuel supply and are important 
# when comparing fossil fuels to emerging alternatives under realistic constraints.
#
# ---------------------------------------------------------------------------

BunkerLogistics {
	LiquidMarketFuels = [Fuel("fossil_fuel_oil")]

	set_distance("*", "*", 1000)	
	set_transport_cost("*", 0.1)
}
