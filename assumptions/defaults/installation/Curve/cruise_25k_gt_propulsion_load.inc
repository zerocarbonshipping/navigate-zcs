# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "cruise_25k_gt_propulsion_load" {
	Table = [
		6	0.7
		7	0.9
		8	1.1
		9	1.4
		10	1.8
		11	2.2
		12	2.8
		13	3.4
		14	4.1
		15	4.8
		16	5.8
		17	6.7
		18	7.7
		19	8.6
		20	9.6
		21	10.7
		22	11.8
		23	13.2
		24	14.9
		25	16.5
	]
	
	Extrapolate = LINEAR
}