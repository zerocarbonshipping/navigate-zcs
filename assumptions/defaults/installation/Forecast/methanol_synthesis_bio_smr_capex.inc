# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of biogas-to-biomethanol synthesis (SMR).
# Unit: USD / ton capacity

Forecast "methanol_synthesis_bio_smr_capex" {
	Table = [
		"01-01-2030"	1250
		"01-01-2050"	1100
	]

	Extrapolate = LINEAR
}
