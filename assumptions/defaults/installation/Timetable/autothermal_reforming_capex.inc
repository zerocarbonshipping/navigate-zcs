# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of an autothermal reforming process plant.
# Unit: USD / ton

Timetable "autothermal_reforming_capex" {
	Table = [
        	            10  	20  	30  	40  	50  	75  	100 	200 	300 	400 	500 	750 	1000	1250
        "01-01-2025"	45925	34805	29594	26377	24125	20513	18283	13856	11781	10501	9604	8166	7279	6657
        "01-01-2050"	45925	34805	29594	26377	24125	20513	18283	13856	11781	10501	9604	8166	7279	6657
	]
	
	Extrapolate = LINEAR
}
