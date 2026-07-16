# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Yearly trade-growth for a vessel segment.
# Unit: Fraction / year

Forecast "trade_growth_tug" {
	Table = [
		"01-01-2025"	0.0313
		"01-01-2030"	0.0225
		"01-01-2035"	0.0173
		"01-01-2040"	0.0138
		"01-01-2045"	0.0130
	]

	Interpolate = PREVIOUS # this works as a stepwise interpolation
	Extrapolate = FLAT
}