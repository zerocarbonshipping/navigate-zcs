# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Regulation "gfs" {
	Measure = INTENSITY
	Scheme = FLEXIBLE

	Scope = WTW
	IncludeSlip = TRUE

	Emissions = Emission("*")
	Fuels = Fuel("*")
		
	Jurisdiction = [Port("port_global"), Port("port_europe")]
	
	RemedialCost = Forecast("gfs_remedial_unit")
	
	SharedThreshold = Forecast("gfs_target_reduction")
	
	set_include_vessel("*", TRUE)
}


Forecast "gfs_target_reduction" {
	Table = [
		"01-01-2025"	1.00
		"31-12-2027"	1.00
		"01-01-2028"	0.96
		"01-01-2029"	0.94
		"01-01-2030"	0.92
		"01-01-2031"	0.876
		"01-01-2032"	0.832
		"01-01-2033"	0.788
		"01-01-2034"	0.744
		"01-01-2035"	0.70
		"01-01-2040"	0.50
		"01-01-2050"	0.00
	]
	
	Multiplier = 93.3
	Extrapolate = FLAT
}

Forecast "gfs_remedial_unit" {
	Table = [
		"01-01-2025"	0
		"31-12-2027"	0
		"01-01-2028"	800
		"01-01-2050"	800
	]
	
	Extrapolate = FLAT
}