# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_tanker_300k_dwt" {
	Table = [
		 8.5,	0.02;
		 9.5,	0.06;
		10.5,	0.12;
		11.5,	0.26;
		12.5,	0.34;
		13.5,	0.14;
		14.5,	0.04;
		15.5,	0.02;
	]
}
