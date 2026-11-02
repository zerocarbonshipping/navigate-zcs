# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Description: Cost of capital for financing a vessel with a DF-ammonia engine.
# Unit: Fraction / year

Forecast "cost_of_capital_vessel_ammonia" {
	Table = [
	    # Higher than the 8.89 % of the other ships of this class
	    # (cost_of_capital_vessel), for the higher risk of a new technology,
	    "01-01-2025"    0.1105
	    "01-01-2027"    0.1105
	    # then easing back to the same rate by 2030, when the technology is
	    # expected to have matured.
	    "01-01-2030"    0.0889
	    "01-01-2050"    0.0889
	]
}
