# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of bio-methanol synthesis (gasification).
# Unit: USD / ton fuel / year

Forecast "methanol_synthesis_bio_gasification_opex" {
	Table = [
		"01-01-2030"	400
		"01-01-2050"	400
	]

	Extrapolate = LINEAR
}
