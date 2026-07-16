# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "cruise_175k_gt_propulsion_load" {
	Table = [
		6	1.5
		7	1.8
		8	2.4
		9	2.9
		10	3.7
		11	4.5
		12	5.9
		13	7.4
		14	9.2
		15	11.2
		16	13.2
		17	15.8
		18	19.1
		19	22.4
		20	26.4
		21	31.0
		22	36.3
		23	42.2
	]
	
	Extrapolate = LINEAR
}