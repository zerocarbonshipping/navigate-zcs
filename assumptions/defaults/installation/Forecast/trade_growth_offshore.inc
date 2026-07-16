# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Yearly trade-growth for a vessel segment.
# Unit: Fraction / year

Forecast "trade_growth_offshore" {
	Table = [
		"01-01-2025"	0.0344
		"01-01-2030"	0.0197
		"01-01-2035"	0.0124
		"01-01-2040"	0.0092
		"01-01-2045"	0.0086
	]

	Interpolate = PREVIOUS # this works as a stepwise interpolation
	Extrapolate = FLAT
}