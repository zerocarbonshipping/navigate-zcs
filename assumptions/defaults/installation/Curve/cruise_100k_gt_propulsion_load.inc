# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "cruise_100k_gt_propulsion_load" {
	Table = [
		6	1.54
		7	1.98
		8	2.42
		9	3.08
		10	3.74
		11	4.95
		12	6.16
		13	7.7
		14	9.35
		15	11
		16	13.2
		17	15.95
		18	18.7
		19	22
		20	25.85
		21	30.25
		22	35.2
	]
	
	Extrapolate = LINEAR
}