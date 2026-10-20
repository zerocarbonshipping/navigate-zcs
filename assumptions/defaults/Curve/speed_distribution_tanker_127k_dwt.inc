# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_tanker_127k_dwt" {
	Table = [
		 7.5,	0.01;
		 8.5,	0.03;
		 9.5,	0.07;
		10.5,	0.13;
		11.5,	0.32;
		12.5,	0.35;
		13.5,	0.08;
		14.5,	0.01;
	]
}
