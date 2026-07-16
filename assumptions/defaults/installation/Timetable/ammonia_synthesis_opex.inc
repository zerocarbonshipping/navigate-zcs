# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of ammonia synthesis.
# Unit: USD / ton

Timetable "ammonia_synthesis_opex" {
	Table = [
        		 	    25	    50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	270	    178 	120 	74  	52  	38  	32  	28  	25  	24  	22  	21  	20  	19  	18
        "01-01-2050"	270	    178 	120 	74  	52  	38  	32  	28  	25  	24  	22  	21  	20  	19  	18
	]

	Extrapolate = LINEAR
}
