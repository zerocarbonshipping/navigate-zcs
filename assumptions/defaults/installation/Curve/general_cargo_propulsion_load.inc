# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "general_cargo_propulsion_load" {
	Table = [
		6.0		0.37
		6.5		0.45
		7.0		0.54
		7.5		0.64
		8.0		0.76
		8.5		0.89
		9.0		1.04
		9.5		1.20
		10.0	1.39
		10.5	1.59
		11.0	1.82
		11.5	2.05
		12.0	2.32
		12.5	2.66
		13.0	3.03
		13.5	3.48
		14.0	4.02
	]
	
	Extrapolate = LINEAR
}
