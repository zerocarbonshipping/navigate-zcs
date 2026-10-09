# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the base ports with the LNG bunker price under test. The %name%
# value is filled in by tests/end_to_end/test_fuel_price_response.py.
Port "*" {
	set_bunker_price_overwrite("liquefied_natural_gas", %lng_price%)    # USD/ton
}
