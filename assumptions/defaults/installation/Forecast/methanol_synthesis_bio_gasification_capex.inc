# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of bio-methanol synthesis (gasification).
# Unit: USD / ton

Forecast "methanol_synthesis_bio_gasification_capex" {
	Table = [
		"01-01-2030"	2700
		"01-01-2050"	2000
	]

	Extrapolate = LINEAR
}
