# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global warming potential of methane emissions as a function of emissions lifetime
# Unit: x = years ; y = Ton CO2 eq./ton emission


Curve "global_warming_potential_methane" {
	Table = [
		20		82.5
		100		29.8
	]

	Extrapolate=FLAT
}
