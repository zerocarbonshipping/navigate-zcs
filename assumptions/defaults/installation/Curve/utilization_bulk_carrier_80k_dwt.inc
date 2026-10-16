# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: cargo capacity utilization when sailing at each speed, 0 where the
# speed is sailed only in ballast and 1 where it is sailed only laden.
# Unit: x = knots ; y = fraction

Curve "utilization_bulk_carrier_80k_dwt" {
	Table = [
		 8.5	1
		 9.5	0.5714285714285714
		10.5	0.6
		11.5	0.6216216216216216
		12.5	0.5833333333333334
		13.5	0.6666666666666666
	]
}
