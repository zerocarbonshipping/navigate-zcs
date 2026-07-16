# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of biogas-to-biomethanol synthesis (SMR).
# Unit: USD / ton capacity / year

Forecast "methanol_synthesis_bio_smr_opex" {
	Table = [
		"01-01-2030"	150
		"01-01-2050"	125
	]

	Extrapolate = LINEAR
}
