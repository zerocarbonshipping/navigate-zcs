# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of e-hydrogen production plant (SOEC).
# Unit: USD / ton

Timetable "hydrogen_electro_soec_capex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	6542	5961	5658	5457	5309	5057	4889	4522	4328	4199	4103	3938	3829	3747
        "01-01-2050"	6542	5961	5658	5457	5309	5057	4889	4522	4328	4199	4103	3938	3829	3747
	]
	
	Extrapolate = LINEAR
}
