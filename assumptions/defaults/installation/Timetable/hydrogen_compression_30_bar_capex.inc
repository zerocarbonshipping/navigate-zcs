# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of a hydrogen compression plant (to 30 bar).
# Unit: USD / ton

Timetable "hydrogen_compression_30_bar_capex" {
	Table = [
						10		20		30		40		50		75		100		200		300		400		500		750		1000	1250
		"01-01-2025"	1129	947		854		794		751		678		630		528		476		443		419		378		351		332
		"01-01-2050"	1129	947		854		794		751		678		630		528		476		443		419		378		351		332
	]
	
	Extrapolate = LINEAR
}
