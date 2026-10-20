# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_bulk_carrier_26k_dwt" {
	Table = [
		 7.5,	0.02;
		 8.5,	0.04;
		 9.5,	0.12;
		10.5,	0.24;
		11.5,	0.34;
		12.5,	0.2;
		13.5,	0.04;
	]
}
