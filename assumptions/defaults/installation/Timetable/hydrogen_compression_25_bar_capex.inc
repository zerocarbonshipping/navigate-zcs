# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of a hydrogen compression plant (to 25 bar).
# Unit: USD / ton

Timetable "hydrogen_compression_25_bar_capex" {
	Table = [
						10		20		30		40		50		75		100		200		300		400		500		750		1000	1250
		"01-01-2025"	1091	910		819		763		720		649		604		506		457		425		401		362		337		318
		"01-01-2050"	1091	910		819		763		720		649		604		506		457		425		401		362		337		318
	]
	
	Extrapolate = LINEAR
}
