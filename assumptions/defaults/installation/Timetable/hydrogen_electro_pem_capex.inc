# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of e-hydrogen production plant (PEM).
# Unit: USD / ton

Timetable "hydrogen_electro_pem_capex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	7140	6372	5975	5714	5522	5197	4983	4519	4276	4117	3999	3798	3665	3567
        "01-01-2050"	7140	6372	5975	5714	5522	5197	4983	4519	4276	4117	3999	3798	3665	3567
	]
	
	Extrapolate = LINEAR
}
