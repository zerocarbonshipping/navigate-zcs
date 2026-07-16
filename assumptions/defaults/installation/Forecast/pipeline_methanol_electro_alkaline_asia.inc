# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Pipeline of cumulative production capacity that is supposed to have been completed in a given year.
# Unit: Tons / day

Forecast "pipeline_methanol_electro_alkaline_asia" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	18
		"01-01-2027"	1124
		"01-01-2028"	1537
	]

	Extrapolate = FLAT
}
