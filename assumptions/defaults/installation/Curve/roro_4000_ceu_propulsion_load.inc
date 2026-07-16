# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "roro_4000_ceu_propulsion_load" {
	Table = [
		10	1.0
		11	1.3
		12	1.7
		13	2.2
		14	2.7
		15	3.1
		16	3.6
		17	4.5
		18	5.7
		19	6.9
		20	8.2
	]
	
	Extrapolate = LINEAR
}
