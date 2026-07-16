# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of grey methanol.
# Unit: USD / ton

Forecast "methanol_grey_cost" {
	Table = [
		"01-01-2025"	 650
		"01-01-2050"	 650
	]
	
	Extrapolate = LINEAR
}
