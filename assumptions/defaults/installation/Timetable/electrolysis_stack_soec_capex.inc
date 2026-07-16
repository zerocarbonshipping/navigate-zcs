# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of SOEC electrolysis.
# Unit: USD / ton

Timetable "electrolysis_stack_soec_capex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	8581	8289	8122	8006	7917	7758	7648	7387	7239	7136	7056	6915	6816	6740
        "01-01-2050"	8581	8289	8122	8006	7917	7758	7648	7387	7239	7136	7056	6915	6816	6740
	]

	Extrapolate = LINEAR
}