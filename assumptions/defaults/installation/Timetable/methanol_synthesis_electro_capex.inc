# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of e-methanol synthesis.
# Unit: USD / ton

Timetable "methanol_synthesis_electro_capex" {
	Table = [
        	            25      50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	4374	3302	2492	1718	1297	979	    830 	739 	675 	627 	589 	558 	532 	509 	490
        "01-01-2050"	4374	3302	2492	1718	1297	979	    830 	739 	675 	627 	589 	558 	532 	509 	490
	]
	
	Extrapolate = LINEAR
}
