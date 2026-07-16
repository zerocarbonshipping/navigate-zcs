# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of e-hydrogen production plant (alkaline).
# Unit: USD / ton

Timetable "hydrogen_electro_alkaline_opex" {
	Table = [
        	            10	    20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	328 	287 	266 	252 	241 	224 	213 	189 	176 	168 	162 	152 	145 	140
        "01-01-2050"	328 	287 	266 	252 	241 	224 	213 	189 	176 	168 	162 	152 	145 	140
	]
	
	Extrapolate = LINEAR
}
