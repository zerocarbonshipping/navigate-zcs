# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Fugitive methane emissions from bio-methane production including credits for improved waste management.
# Unit: ton emission / ton fuel

Forecast "methane_synthesis_and_liquefaction_wtt_methane" {
	Table = [
		"01-01-2025"	0.0242
		"01-01-2030"	0.0151
		"01-01-2035"	0.0106
		"01-01-2040"	0.0091
		"01-01-2045"	0.0076
		"01-01-2050"	0.0060
	]
	
	Extrapolate = LINEAR
	LowerBound = 0  # value at zero fugitive emissions
}
