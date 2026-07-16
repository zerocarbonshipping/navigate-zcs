# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of used cooking oil.
# Unit: USD / ton

Forecast "used_cooking_oil_cost_europe" {
	Table = [
		"01-01-2025"	 1130
		"01-01-2050"	 1130
	]
	
	Extrapolate = LINEAR
}
