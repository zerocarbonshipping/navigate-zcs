# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "offshore_propulsion_load" {
	Table = [
		 10 	 1.8 
		 11 	 2.1 
		 12 	 2.2 
		 13 	 2.6 
		 14 	 2.9 
		 15 	 3.0 
		 16 	 3.3 
		 17 	 3.7 
		 18 	 4.3 
		 19 	 4.9 
		 20 	 5.8 
	]
	
	Extrapolate = LINEAR
}