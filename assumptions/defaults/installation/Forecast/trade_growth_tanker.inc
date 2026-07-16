# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Yearly trade-growth for a vessel segment.
# Unit: Fraction / year

Forecast "trade_growth_tanker" {
	Table = [
		"01-01-2025"	0.0219
		"01-01-2030"	0.0140
		"01-01-2035"	0.0074
		"01-01-2040"	0.0069
		"01-01-2045"	0.0043
	]

	Interpolate = PREVIOUS # this works as a stepwise interpolation
	Extrapolate = FLAT
}