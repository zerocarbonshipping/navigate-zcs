# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_bulk_carrier_52k_dwt" {
	Table = [
		 8.5,	0.02;
		 9.5,	0.07;
		10.5,	0.22;
		11.5,	0.35;
		12.5,	0.25;
		13.5,	0.08;
		14.5,	0.01;
	]
}
