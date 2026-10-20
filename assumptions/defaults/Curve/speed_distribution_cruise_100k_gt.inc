# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_cruise_100k_gt" {
	Table = [
		10,	0.05;
		12,	0.09;
		14,	0.18;
		15,	0.09;
		16,	0.14;
		17,	0.09;
		18,	0.27;
		21,	0.09;
	]
}
