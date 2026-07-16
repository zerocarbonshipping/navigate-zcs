# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of methane liquefaction.
# Unit: USD / ton

Timetable "methane_liquefaction_opex" {
	Table = [
						250		5500
		"01-01-2025"	0		0
		"01-01-2050"	0		0
	]

	Extrapolate = LINEAR
}
