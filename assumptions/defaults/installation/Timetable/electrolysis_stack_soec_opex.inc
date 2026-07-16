# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of SOEC electrolysis.
# Unit: USD / ton

Timetable "electrolysis_stack_soec_opex" {
	Table = [
        	            10  	20	    30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	300	    290 	284 	280 	277 	272 	268 	259 	253 	250 	247 	242 	239 	236
        "01-01-2050"	300	    290 	284 	280 	277 	272 	268 	259 	253 	250 	247 	242 	239 	236
	]
	
	Extrapolate = LINEAR
}
