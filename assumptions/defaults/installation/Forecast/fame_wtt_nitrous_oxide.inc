# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Well-to-tank nitrous oxide emissions of FAME.
# Unit: ton emissions / ton feedstock.

Forecast "fame_wtt_nitrous_oxide" {
	Table = [
		"01-01-2025" 1.462e-5
		"01-01-2050" 1.462e-5
	]
	
	Extrapolate = FLAT
}
