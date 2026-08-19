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
	
	set_vessel_threshold("*", Forecast("gfs_target_reduction"))
	
	set_include_vessel("*", TRUE)
}


Forecast "gfs_target_reduction" {
	Table = [
		"01-01-2025"	1.00
		"31-12-2027"	1.00
		"01-01-2028"	0.96
		"01-01-2029"	0.94
		"01-01-2030"	0.95
		"01-01-2035"	0.75
		"01-01-2050"	0.30
	]
	
	Multiplier = 93.3
	Extrapolate = FLAT
}

Forecast "gfs_remedial_unit" {
	Table = [
		"01-01-2025"	0
		"31-12-2027"	0
		"01-01-2028"	300
		"01-01-2050"	300
	]
	
	Extrapolate = FLAT
}