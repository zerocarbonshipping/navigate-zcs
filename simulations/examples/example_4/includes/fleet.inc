# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FLEET - Panamax bulk carriers (~80,000 DWT), four configurations of one hull.
# All four share hull, propulsion curve, cargo capacity and OPEX.
#
# This file never describes the ships themselves. It reaches for them with
# Copy Vessel, which takes a vessel out of the assumptions library and gives the
# copy a local name, so ship_lng is a copy of bulk_carrier_80k_dwt_ice_methane.

Copy Vessel "bulk_carrier_80k_dwt_ice_oil"      "ship_oil"
Copy Vessel "bulk_carrier_80k_dwt_ice_methane"  "ship_lng"
Copy Vessel "bulk_carrier_80k_dwt_ice_methanol" "ship_methanol"
Copy Vessel "bulk_carrier_80k_dwt_ice_ammonia"  "ship_ammonia"

Fleet "copper_trade" {
	Vessels = [Vessel("ship_oil"),
	           Vessel("ship_lng"),
	           Vessel("ship_methanol"),
	           Vessel("ship_ammonia")]

	InitialVessels = 300 # Arbitrary number (represents 8% of the world Panamax fleet)
	InitialSplit = [1.0, 0.0, 0.0, 0.0] # Only ship oil vessels

	# The age spread of the world's 80k DWT bulk carriers, taken from the library.
	# Navigate splits the fleet into one cohort per year of age.
	InitialAgeDistribution = [
		Curve("age_dist_bulk_carrier_80k_dwt_oil"),
		0,
		0,
		0
	]
	# Note: Orderbooks omitted for this example since the library's are sized for
	# the whole world

	# Library trade growth for this class: ~2.2%/yr stepping down to ~1.4%.
	# Newbuilds are therefore a mix of replacement and expansion.
	TradeGrowth = Forecast("trade_growth_bulk_carrier")

	# Retrofit costs, figures for this class (Fleet/bulk_carrier_80k_dwt.inc).
	# These lines set which retrofits are possible and what each costs: an oil
	# ship can be converted to methanol or ammonia, and an LNG ship to ammonia.
	# No line converts a ship to LNG, so an LNG ship can only be bought new.
	set_fuel_conversion_cost("ship_oil", "ship_methanol", 17.5e6)
	set_fuel_conversion_cost("ship_oil", "ship_ammonia", 24.1e6)
	set_fuel_conversion_cost("ship_lng", "ship_ammonia", 14.2e6)

	AllowSpeedManagement = TRUE
	MaximumSpeedChange = 0.7
}
