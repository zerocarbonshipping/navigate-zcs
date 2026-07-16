# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: The percentage of emissions the maritime industry will be required to pay for under the EU ETS regulation.
# Unit: Fraction

Forecast "eu_ets_maritime_phase_in" {
	Table = [
		"01-01-2024"	0.4
		"01-01-2025"	0.7
		"01-01-2026"	1
		"01-01-2050"	1
	]
	
	Extrapolate = FLAT
}
