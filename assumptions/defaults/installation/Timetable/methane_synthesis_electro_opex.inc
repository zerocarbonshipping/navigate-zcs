# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of e-methane synthesis.
# Unit: USD / ton

Timetable "methane_synthesis_electro_opex" {
	Table = [
			            25  	50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	165	    107 	72  	44  	32  	24  	21  	19  	17  	16  	15  	15  	14  	14  	13
		"01-01-2050"	165	    107 	72  	44  	32  	24  	21  	19  	17  	16  	15  	15  	14  	14  	13
	]

	Extrapolate = LINEAR
}
