# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of a hydrogen compression plant (to 10 bar).
# Unit: USD / ton

Timetable "hydrogen_compression_10_bar_opex" {
	Table = [
						10		20		30		40		50		75		100		200		300		400		500		750		1000	1250
		"01-01-2025"	140		93		75		64		58		47		41		30		26		23		21		18		17		15
		"01-01-2050"	140		93		75		64		58		47		41		30		26		23		21		18		17		15
	]
	
	Extrapolate = LINEAR
}
