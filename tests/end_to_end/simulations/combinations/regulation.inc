# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A regulation on every emission of every fuel at both ports, with the
# measure, scheme, scope and threshold adjustment under test. The %name%
# values are filled in by tests/end_to_end/test_regulation_combinations.py.
#
# The threshold is zero, which no vessel can meet in any measure or scope:
# both fuels emit in every scope. The regulation is therefore non-compliant
# at every step whatever the combination, which is what the test reads.
Regulation "combination_regulation" {
	Measure = %measure%
	Scheme = %scheme%
	Scope = %scope%
	AllowThresholdAdjustment = %allow_threshold_adjustment%

	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("port_global"), Port("port_europe")]

	RemedialCost = 100                  # USD per unit of non-compliance

	set_vessel_threshold("*", 0)
	set_include_vessel("*", TRUE)
}
