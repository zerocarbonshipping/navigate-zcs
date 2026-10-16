# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: cargo capacity utilization when sailing at each speed, 0 where the
# speed is sailed only in ballast and 1 where it is sailed only laden.
# Unit: x = knots ; y = fraction

Curve "utilization_tanker_127k_dwt" {
	Table = [
		 7.5	0
		 8.5	0.3333333333333333
		 9.5	0.42857142857142855
		10.5	0.38461538461538464
		11.5	0.40625
		12.5	0.4
		13.5	0.375
		14.5	0
	]
}
