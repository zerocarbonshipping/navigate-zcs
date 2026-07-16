# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of alkaline electrolysis.
# Unit: USD / ton

Timetable "electrolysis_stack_alkaline_capex" {
	Table = [
                        10	    20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	5022	4851	4753	4685	4633	4540	4475	4323	4236	4176	4129	4047	3989	3945
        "01-01-2050"	5022	4851	4753	4685	4633	4540	4475	4323	4236	4176	4129	4047	3989	3945
	]
	
	Extrapolate = LINEAR
}
