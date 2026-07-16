# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of e-hydrogen production plant (SOEC).
# Unit: USD / ton

Timetable "hydrogen_electro_soec_opex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	229 	209 	198 	191 	186 	177 	171 	158 	151 	147 	144 	138 	134 	131
        "01-01-2050"	229	    209 	198 	191 	186 	177 	171 	158 	151 	147 	144 	138 	134 	131
	]
	
	Extrapolate = LINEAR
}
