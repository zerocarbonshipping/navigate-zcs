# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "roro_7000_ceu_propulsion_load" {
	Table = [
		10	2.0
		11	2.6
		12	3.4
		13	4.4
		14	5.4
		15	6.7
		16	8.1
		17	9.9
		18	11.9
	]
	
	Extrapolate = LINEAR
}
