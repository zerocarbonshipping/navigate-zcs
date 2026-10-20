# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: share of the time at sea sailed at each speed.
# Unit: x = knots ; y = fraction

Curve "speed_distribution_bulk_carrier_80k_dwt" {
	Table = [
		 8.5,	0.01;
		 9.5,	0.07;
		10.5,	0.25;
		11.5,	0.37;
		12.5,	0.24;
		13.5,	0.06;
	]
}
