# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Combined upgrading + liquefaction CAPEX.
# Unit: USD / ton LBM annual capacity

Forecast "methane_upgrading_and_liquefaction_bio_capex" {
	Table = [
		"01-01-2025"	2000
		"01-01-2050"	2000
	]

	Extrapolate = LINEAR
}
