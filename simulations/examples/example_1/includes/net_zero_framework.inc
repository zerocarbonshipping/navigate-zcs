# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# -------------------------- NET ZERO FRAMEWORK REGULATIONS --------------------------
#
# Implements an interpretation of the IMO Net Zero Framework (January 2026).
# Defines a well-to-wake (WTW) emissions intensity pathway aligned with net-zero goals.
# Applies across fuels and vessel types, with adjustable scope, jurisdiction, and coverage.
#
# -------------------------------------------------------------------------------------

Regulation "net_zero_framework" {
	Measure = INTENSITY
	Scheme = FLEXIBLE

	Scope = WTW
	IncludeSlip = TRUE

	Emissions = Emission("*")
	Fuels = Fuel("*")
		
	Jurisdiction = [Port("singapore"), Port("rotterdam"), Port("hamburg"), Port("aalborg")]
	 
	RemedialCost = Forecast("net_zero_framework_remedial")
	
	SharedThreshold = Forecast("net_zero_framework_z_values")
	
	set_include_vessel("*", TRUE)
}

Forecast "net_zero_framework_z_values" {
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
		"01-01-2040"	0.35
		"01-01-2050"	0.05
	]
	
	Multiplier = 93.3
	Extrapolate = FLAT
}

# Here you can change the remedial cost
Forecast "net_zero_framework_remedial" {
	Table = [
		"01-01-2025"	0
		"31-12-2027"	0
		"01-01-2028"	380
	]
	
	Extrapolate = FLAT
}