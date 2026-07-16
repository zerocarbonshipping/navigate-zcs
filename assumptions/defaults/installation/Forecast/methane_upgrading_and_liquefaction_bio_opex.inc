# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Combined upgrading + liquefaction OPEX.
# Unit: USD / ton LBM / yr

Forecast "methane_upgrading_and_liquefaction_bio_opex" {
	Table = [
		"01-01-2025"	200
		"01-01-2050"	200
	]

	Extrapolate = LINEAR
}
