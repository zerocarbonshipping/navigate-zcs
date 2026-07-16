# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of ammonia synthesis.
# Unit: USD / ton

Timetable "ammonia_synthesis_capex" {
	Table = [
        	            25	    50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	3069	2454	1963	1461	1168	934 	820 	747 	695 	656 	624 	598 	575 	556 	539
        "01-01-2050"	3069	2454	1963	1461	1168	934	    820 	747 	695 	656 	624 	598 	575 	556 	539
	]
	
	Extrapolate = LINEAR
}
