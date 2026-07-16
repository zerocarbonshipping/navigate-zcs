# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Well-to-tank carbon dioxide emissions of FAME.
# Unit: ton emissions / ton feedstock.

Forecast "fame_wtt_carbon_dioxide" {
	Table = [
		"01-01-2025" 0.627
		"01-01-2050" 0.627
	]
	
	Extrapolate = FLAT
}
