# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Combined upgrading + liquefaction electricity consumption.
# Unit: MWh / ton LBM

Forecast "methane_upgrading_and_liquefaction_bio_energy" {
	Table = [
		"01-01-2025"	1.2
		"01-01-2050"	1.2
	]

	Extrapolate = LINEAR
}
