# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Pipeline of cumulative production capacity that is supposed to have been completed in a given year.
# Unit: Tons / day

Forecast "pipeline_ammonia_electro_alkaline_africa" {
	Table = [
		"01-01-2025"	0
		"01-01-2026"	4
		"01-01-2027"	4
		"01-01-2028"	4
	]

	Extrapolate = FLAT
}