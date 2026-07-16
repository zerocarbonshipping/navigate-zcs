# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of an autothermal reforming process plant.
# Unit: USD / ton

Timetable "autothermal_reforming_opex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	2099	1591	1352	1205	1102	937	    836 	633 	538 	480 	439 	373 	333 	304
        "01-01-2050"	2099	1591	1352	1205	1102	937	    836 	633 	538 	480 	439 	373 	333 	304
	]
	
	Extrapolate = LINEAR
}
