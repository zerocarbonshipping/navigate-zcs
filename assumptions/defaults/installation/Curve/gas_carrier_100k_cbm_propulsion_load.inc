# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "gas_carrier_100k_cbm_propulsion_load" {
	Table = [
		10	2.0
		11	2.8
		12	3.6
		13	4.6
		14	5.8
		15	7.0
		16	8.5
		17	10.2
		18	12.0
	]
	
	Extrapolate = LINEAR
}
