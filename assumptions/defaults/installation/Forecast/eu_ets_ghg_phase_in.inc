# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: The phase in of methane (CH4) and nitrous oxide (N2O) emissions under the EU ETS regulation.
# Unit: Fraction

Forecast "eu_ets_ghg_phase_in" {
	Table = [
		"01-01-2024"	0.
		"01-01-2026"	1.
	]
	
	Extrapolate = FLAT
	Interpolate = PREVIOUS
}
