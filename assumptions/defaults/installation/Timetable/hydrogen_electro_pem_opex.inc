# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of e-hydrogen production plant (PEM).
# Unit: USD / ton

Timetable "hydrogen_electro_pem_opex" {
	Table = [
        	            10  	20  	30	    40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	143 	127 	120 	114 	110 	104 	100 	90  	86  	82  	80  	76  	73  	71
        "01-01-2050"	143 	127 	120 	114 	110 	104 	100 	90  	86  	82  	80  	76  	73  	71
	]
	
	Extrapolate = LINEAR
}
