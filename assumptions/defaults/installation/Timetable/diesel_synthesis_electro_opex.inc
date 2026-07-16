# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Operational expenditure of e-diesel synthesis.
# Unit: USD / ton

Timetable "diesel_synthesis_electro_opex" {
	Table = [
					    25  	50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	289 	205 	150 	105 	83  	67  	60  	56  	53  	50  	48  	47  	45  	44  	43
		"01-01-2050"	289 	205 	150 	105 	83  	67  	60  	56  	53  	50  	48  	47  	45  	44  	43
	]
	
	Extrapolate = LINEAR
}
