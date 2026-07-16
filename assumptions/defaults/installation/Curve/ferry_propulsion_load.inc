# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: power demand needed to sail different speeds for given vessel.
# Unit: x = knots ; y = MW

Curve "ferry_propulsion_load" {
	Table = [
		 10 	 2.0 
		 11 	 2.1 
		 12 	 2.3 
		 13 	 2.4 
		 14 	 2.6 
		 15 	 2.8 
		 16 	 3.0 
		 17 	 3.2 
		 18 	 3.4 
		 19 	 3.7 
		 20 	 4.1 
		 21 	 4.5 
		 22 	 5.0 
	]
	
	Extrapolate = LINEAR
}