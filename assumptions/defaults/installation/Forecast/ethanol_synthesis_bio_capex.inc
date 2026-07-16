# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of bio-ethanol synthesis (cellulosic).
# Unit: USD / ton annual capacity

Forecast "ethanol_synthesis_bio_capex" {
	Table = [
		"01-01-2030"	3640
		"01-01-2050"	3000
	]

	Extrapolate = LINEAR
}
