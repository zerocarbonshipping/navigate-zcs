# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# FLEET - Panamax bulk carriers (~80,000 DWT): the library's fleet for this class.
# It brings the four configurations of one hull, which share hull, propulsion
# curve, cargo capacity and OPEX; today's split between them (99.9% fuel oil,
# 0.1% LNG) and the ships' ages; trade growth; retrofit costs; speed management;
# and the seven efficiency technologies, with the share of today's ships
# already fitted with each.
# Only what makes this one trade rather than the world's fleet is set here.

Import Fleet "bulk_carrier_80k_dwt"

# Imported by name too, so that the Vessel "bulk_carrier_80k_dwt_*" block of
# route.inc matches them: a wildcard block matches only the nodes a deck
# declares, not those its references bring in.
Import Vessel "bulk_carrier_80k_dwt_ice_oil"
Import Vessel "bulk_carrier_80k_dwt_ice_methane"
Import Vessel "bulk_carrier_80k_dwt_ice_methanol"
Import Vessel "bulk_carrier_80k_dwt_ice_ammonia"

Fleet "bulk_carrier_80k_dwt" {
	InitialVessels = 300 # Arbitrary number (represents 8% of the world Panamax fleet)

	# the library's orderbooks are sized for the whole world
	Orderbooks = [0, 0, 0, 0]

	# The library defines no technology-specific rate, so this makes Navigate's
	# own fallback explicit: same value, no warning, nothing invented.
	TechnologyCostOfCapital = Variable("cost_of_capital_vessel")
}
