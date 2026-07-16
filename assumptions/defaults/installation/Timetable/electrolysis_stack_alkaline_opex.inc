# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of alkaline electrolysis.
# Unit: USD / ton

Timetable "electrolysis_stack_alkaline_opex" {
	Table = [
        	            10	    20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	201 	194 	190 	187 	185 	182 	179 	173 	169 	167 	165 	162 	160 	158
        "01-01-2050"	201	    194 	190 	187 	185 	182 	179 	173 	169 	167 	165 	162 	160 	158
	]
	
	Extrapolate = LINEAR
}
