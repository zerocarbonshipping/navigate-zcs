# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "other_propulsion_load" {
	Table = [
		 10 	 0.15
		 11 	 0.25 
		 12 	 0.30 
		 13 	 0.35
		 14 	 0.40
		 15 	 0.50 
	]
	
	Extrapolate = LINEAR
}
