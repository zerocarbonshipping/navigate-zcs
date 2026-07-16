# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of container fleet

Fleet "container_fleet" {	
	Vessels = [Vessel("container_ice_oil"), Vessel("container_ice_methane")] 	
	InitialVessels = 100 
	TradeGrowth = 0.05
}
