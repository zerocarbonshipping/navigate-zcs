# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of e-methane synthesis.
# Unit: USD / ton

Timetable "methane_synthesis_electro_capex" {
	Table = [
			            25  	50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	1097	948	    820 	676 	585 	505 	464 	437 	417 	401 	389 	378 	369 	360 	353
		"01-01-2050"	1097	948	    820 	676 	585 	505 	464 	437 	417 	401 	389 	378 	369 	360 	353
	]
	
	Extrapolate = LINEAR
}
