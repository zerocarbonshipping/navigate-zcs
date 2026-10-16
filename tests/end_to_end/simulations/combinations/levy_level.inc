# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the levy of levy.inc at another level. The %name% value is filled
# in by tests/end_to_end/test_scaling.py.
Levy "combination_levy" {
	Level = %level%                         # USD/ton CO2-eq
}
