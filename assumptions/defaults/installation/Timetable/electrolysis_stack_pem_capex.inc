# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of PEM electrolysis.
# Unit: USD / ton

Timetable "electrolysis_stack_pem_capex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	6862	6628	6495	6402	6331	6204	6116	5907	5789	5706	5643	5529	5451	5390
        "01-01-2050"	6862	6628	6495	6402	6331	6204	6116	5907	5789	5706	5643	5529	5451	5390
	]
	
	Extrapolate = LINEAR
}
