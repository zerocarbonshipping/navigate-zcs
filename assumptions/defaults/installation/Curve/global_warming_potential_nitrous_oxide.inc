# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Global warming potential of nitrous oxide emissions as a function of emissions lifetime
# Unit: x = years ; y = Ton CO2 eq./ton emission

Curve "global_warming_potential_nitrous_oxide" {
	Table = [
		20		273
		100		273
	]

	Extrapolate=FLAT
}