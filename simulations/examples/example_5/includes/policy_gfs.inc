# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# GLOBAL FUEL STANDARD - the IMO Net-Zero Framework as approved in draft at
# MEPC 83 (April 2025). Not adopted: the October 2025 session adjourned for a
# year, and the extraordinary session resumes on 4 December 2026.
#
# It caps a ship's well-to-wake GHG fuel intensity (GFI) against the 2008
# reference, 93.3 gCO2e/MJ, at two levels:
#   direct compliance target  -17 % in 2028, -21 % in 2030, -43 % in 2035;
#                             a deficit below it costs 100 USD/t CO2e (Tier 1)
#   base target               -4 % in 2028, -8 % in 2030, -30 % in 2035;
#                             a deficit below it costs 380 USD/t CO2e (Tier 2)
# Here they are two regulations that add up: gfs_tier_1 charges 100 below the
# direct target and gfs_tier_2 a further 280 below the base target, so a ton
# beyond the base target costs 380 in all.
# The framework restricts how surplus units can be used; this deck lets them pool freely.
#
# Applies to ships of 5,000 GT and above on international voyages (IMO FAQ), so
# the international ships (intl_*) only. A deck that extends it to the regional
# ships adds set_include_vessel("reg_*", TRUE) after this file.
#
# INVENTED beyond the text: the prices are set for 2028-2030 only and the
# targets end in 2035; both are held flat afterwards.

Regulation "gfs_tier_1" {
	Measure = INTENSITY
	Scheme = FLEXIBLE
	Scope = WTW
	IncludeSlip = TRUE
	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("jamaica"), Port("trinidad"), Port("martinique"), Port("miami")]
	RemedialCost = Forecast("gfs_tier_1_price")
	SharedThreshold = Forecast("gfs_direct_compliance_target")
	set_include_vessel("intl_*", TRUE)
}

Regulation "gfs_tier_2" {
	Measure = INTENSITY
	Scheme = FLEXIBLE
	Scope = WTW
	IncludeSlip = TRUE
	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("jamaica"), Port("trinidad"), Port("martinique"), Port("miami")]
	RemedialCost = Forecast("gfs_tier_2_extra_price")
	SharedThreshold = Forecast("gfs_base_target")
	set_include_vessel("intl_*", TRUE)
}

# fraction of the 2008 reference that is allowed
Forecast "gfs_direct_compliance_target" {
	Table = [
		"01-01-2025"	1.00
		"31-12-2027"	1.00
		"01-01-2028"	0.83
		"01-01-2030"	0.79
		"01-01-2035"	0.57
	]
	Multiplier = 93.3
	Extrapolate = FLAT
}

Forecast "gfs_base_target" {
	Table = [
		"01-01-2025"	1.00
		"31-12-2027"	1.00
		"01-01-2028"	0.96
		"01-01-2030"	0.92
		"01-01-2035"	0.70
	]
	Multiplier = 93.3
	Extrapolate = FLAT
}

Forecast "gfs_tier_1_price" {
	Table = [
		"01-01-2025"	0
		"31-12-2027"	0
		"01-01-2028"	100
		"01-01-2050"	100
	]
	Extrapolate = FLAT
}

Forecast "gfs_tier_2_extra_price" {
	Table = [
		"01-01-2025"	0
		"31-12-2027"	0
		"01-01-2028"	280
		"01-01-2050"	280
	]
	Extrapolate = FLAT
}
