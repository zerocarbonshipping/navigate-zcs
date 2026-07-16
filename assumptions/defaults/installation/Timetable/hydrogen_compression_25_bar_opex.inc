# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of a hydrogen compression plant (to 25 bar).
# Unit: USD / ton

Timetable "hydrogen_compression_25_bar_opex" {
	Table = [
						10		20		30		40		50		75		100		200		300		400		500		750		1000	1250
		"01-01-2025"	150		102		83		72		64		53		47		35		30		27		25		22		20		18
		"01-01-2050"	150		102		83		72		64		53		47		35		30		27		25		22		20		18
	]

	Extrapolate = LINEAR
}