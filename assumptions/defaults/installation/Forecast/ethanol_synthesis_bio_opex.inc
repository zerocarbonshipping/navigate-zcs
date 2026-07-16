# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of bio-ethanol synthesis (cellulosic, excl. energy and feedstock).
# Unit: USD / ton annual capacity / year

Forecast "ethanol_synthesis_bio_opex" {
	Table = [
		"01-01-2030"	585
		"01-01-2050"	420
	]

	Extrapolate = LINEAR
}
