# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# A WTW carbon levy ramping from a mild to a decisive price signal, so the
# baseline captures both a near-BAU phase and a levy-driven transition. The
# level trajectory is a deck-sizing input (tuned so the transition happens
# inside the simulated horizon).

Levy "carbon_levy" {
	Scheme = PENALTY
	Scope = WTW
	IncludeSlip = TRUE

	Emissions = Emission("*")
	Fuels = Fuel("*")

	Jurisdiction = [Port("port_global"), Port("port_europe")]

	Level = Forecast("carbon_levy_level")

	# include_vessel defaults to FALSE per vessel: an unset levy collects
	# nothing
	set_include_vessel("*", TRUE)
}

Forecast "carbon_levy_level" {
	# USD/ton CO2-eq. Sized around the deck's break-even: pinned e-ammonia
	# costs ~910 USD/ton (~49 USD/GJ) against oil at ~12 USD/GJ with a WTW
	# intensity of ~0.094 ton CO2/GJ, so oil's levy-inclusive cost crosses
	# ammonia's near a 400 USD/ton level — mid-ramp, giving the baseline a
	# near-BAU phase and a levy-driven transition inside the horizon.
	Table = [
		"01-01-2026"	50
		"01-01-2035"	400
		"01-01-2045"	1000
	]

	Extrapolate = FLAT
}
