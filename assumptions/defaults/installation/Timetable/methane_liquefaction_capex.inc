# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of methane liquefaction.
# Unit: USD / ton

Timetable "methane_liquefaction_capex" {
	Table = [
						250		5500
		"01-01-2025"	2250	2250
		"01-01-2050"	2000	2000
	]
	
	Extrapolate = LINEAR
}
