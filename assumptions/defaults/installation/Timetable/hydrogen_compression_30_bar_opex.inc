# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of a hydrogen compression plant (to 30 bar).
# Unit: USD / ton

Timetable "hydrogen_compression_30_bar_opex" {
	Table = [
						10		20		30		40		50		75		100		200		300		400		500		750		1000	1250
		"01-01-2025"	152		104		85		73		66		55		48		36		31		28		26		22		20		19
		"01-01-2050"	152		104		85		73		66		55		48		36		31		28		26		22		20		19
	]

	Extrapolate = LINEAR
}