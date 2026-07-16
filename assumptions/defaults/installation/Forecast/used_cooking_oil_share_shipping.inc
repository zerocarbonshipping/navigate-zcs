# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Shipping's share of used cooking oil in Europe (imported and domestic).
# Unit: ton / year

Forecast "used_cooking_oil_share_shipping" {
	Table = [
		"01-01-2025"	0.023
		"01-01-2030"	0.038
	]
		
	LowerBound = 0
	UpperBound = 1
	
	Extrapolate = LINEAR
}
