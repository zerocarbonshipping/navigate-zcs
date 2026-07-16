# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Fraction of fleet (column 2) to install a technology at a given payback period (column 1) currently.
# Unit: Years (column 1), Fraction of fleet (column 2).

Curve "technology_uptake" {
	Table = [
		 0	1.000
		 1	0.607
		 2	0.368
		 3	0.223
		 4	0.120
		 5	0.050
		 6	0.010
		 7	0.000
	   1e9	0.000  # included to supress extrapolation warnings
	]
	
	Extrapolate = FLAT
}