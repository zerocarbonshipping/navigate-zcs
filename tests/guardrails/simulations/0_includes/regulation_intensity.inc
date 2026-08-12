# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# A synthetic GHG-intensity regulation (modeled on the GFS scenario
# regulation) whose shrinking threshold imposes alternative-fuel demand. The
# threshold trajectory and remedial cost are deck-sizing inputs (tuned so the
# implied ammonia demand always exceeds what the constrained Producer can
# supply); the asserted property does not depend on their exact values.

Regulation "intensity_regulation" {
	Measure = INTENSITY
	Scheme = FLEXIBLE

	Scope = WTW
	IncludeSlip = TRUE

	Emissions = Emission("*")
	Fuels = Fuel("*")

	Jurisdiction = [Port("port_global"), Port("port_europe")]

	RemedialCost = Forecast("intensity_remedial_unit")

	SharedThreshold = Forecast("intensity_target_reduction")

	set_include_vessel("*", TRUE)
}

# The threshold shrinks from the very first time-step so the demand signal
# exists throughout the simulation — the assertion window must not need a
# head exclusion for regulation onset.
Forecast "intensity_target_reduction" {
	Table = [
		"01-01-2026"	1.00
		"01-01-2027"	0.97
		"01-01-2035"	0.73
		"01-01-2050"	0.28
	]

	# baseline WTW GHG intensity in gCO2e/MJ
	Multiplier = 93.3

	Extrapolate = FLAT
}

Forecast "intensity_remedial_unit" {
	# sized well above the e-ammonia abatement cost, so compliance via
	# alternative fuel is always preferred over paying the remedial cost
	Table = [
		"01-01-2026"	1000
		"01-01-2050"	1000
	]

	Extrapolate = FLAT
}
