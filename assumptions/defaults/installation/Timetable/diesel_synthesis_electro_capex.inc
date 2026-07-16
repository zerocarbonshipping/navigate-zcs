# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Capital expenditure of e-diesel synthesis.
# Unit: USD / ton

Timetable "diesel_synthesis_electro_capex" {
	Table = [
			            25  	50  	100 	250 	500 	1000	1500	2000	2500	3000	3500	4000	4500	5000	5500
        "01-01-2025"	3576	3113	2710	2256	1964	1710	1577	1488	1423	1373	1331	1296	1266	1239	1216
		"01-01-2050"	3576	3113	2710	2256	1964	1710	1577	1488	1423	1373	1331	1296	1266	1239	1216
	]
	
	Extrapolate = LINEAR
}
