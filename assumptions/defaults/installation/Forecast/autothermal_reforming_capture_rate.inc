# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: CO2 capture rate of autothermal reforming process.
# Unit: USD / ton

Forecast "autothermal_reforming_capture_rate" {
	Table = [
		"01-01-2025"	0.95
		"01-01-2050"	0.95
	]
	
	Extrapolate = LINEAR
	LowerBound = 0
	UpperBound = 1
}
