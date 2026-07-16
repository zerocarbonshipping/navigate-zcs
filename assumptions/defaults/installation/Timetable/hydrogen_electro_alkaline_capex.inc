# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of e-hydrogen production plant (alkaline).
# Unit: USD / ton

Timetable "hydrogen_electro_alkaline_capex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	8210	7173	6641	6292	6037	5607	5325	4718	4405	4199	4049	3794	3626	3503
        "01-01-2050"	8210	7173	6641	6292	6037	5607	5325	4718	4405	4199	4049	3794	3626	3503
	]
	
	Extrapolate = LINEAR
}
