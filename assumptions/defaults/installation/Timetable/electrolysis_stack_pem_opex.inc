# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of PEM electrolysis.
# Unit: USD / ton

Timetable "electrolysis_stack_pem_opex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	137 	133 	130 	128 	127 	124 	122 	118 	116 	114 	113 	111 	109 	108
        "01-01-2050"	137 	133 	130 	128 	127 	124 	122 	118 	116 	114 	113 	111 	109 	108
	]
	
	Extrapolate = LINEAR
}
