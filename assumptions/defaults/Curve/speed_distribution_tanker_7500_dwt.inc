# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_tanker_7500_dwt" {
	Table = [
		 6.5,	0.02;
		 7.5,	0.04;
		 8.5,	0.08;
		 9.5,	0.14;
		10.5,	0.2;
		11.5,	0.24;
		12.5,	0.18;
		13.5,	0.08;
		14.5,	0.02;
	]
}
