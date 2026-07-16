# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of a hydrogen compression plant (to 10 bar).
# Unit: USD / ton

Timetable "hydrogen_compression_10_bar_capex" {
	Table = [
						10		20		30		40		50		75		100		200		300		400		500		750		1000	1250
		"01-01-2025"	880		732		663		614		581		525		487		408		369		343		324		292		272		257
		"01-01-2050"	880		732		663		614		581		525		487		408		369		343		324		292		272		257
	]
	
	Extrapolate = LINEAR
}
