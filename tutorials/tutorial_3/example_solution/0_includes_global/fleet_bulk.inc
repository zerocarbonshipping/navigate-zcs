# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of bulk fleet

Fleet "bulk_fleet" {	
	Vessels = [Vessel("bulk_ice_methanol"), Vessel("bulk_ice_ammonia")] 	
	InitialVessels = 100
	TradeGrowth = 0.05
}
