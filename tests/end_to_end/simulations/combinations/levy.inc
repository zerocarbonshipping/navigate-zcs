# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# A levy on every emission of every fuel at both ports, with the scheme and
# scope under test. The %name% values are filled in by
# tests/end_to_end/test_levy_combinations.py, which also chooses the lower
# threshold per scope so that oil lies above it and LNG below it, from the
# emission factors pinned in 0_includes/fuels_ports.inc.
Levy "combination_levy" {
	Scheme = %scheme%
	Scope = %scope%

	Emissions = Emission("*")
	Fuels = Fuel("*")
	Jurisdiction = [Port("port_global"), Port("port_europe")]

	Level = 100                             # USD/ton CO2-eq
	LowerThreshold = %lower_threshold%      # kg CO2-eq/GJ

	set_include_vessel("*", TRUE)
}
