# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "tug_propulsion_load" {
	Table = [
		 10 	 0.6 
		 11 	 1.1 
		 12 	 1.5 
		 13 	 2.1 
		 14 	 2.69
	]
	
	Extrapolate = LINEAR
}