# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the levy of levy.inc with an upper threshold. The %name% value is
# filled in by tests/end_to_end/test_levy_combinations.py, below oil's
# emission factor in the scope under test, so the cap binds on oil.
Levy "combination_levy" {
	UpperThreshold = %upper_threshold%      # kg CO2-eq/GJ
}
