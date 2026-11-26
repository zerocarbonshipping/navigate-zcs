# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the base fleet with an oil -> methane conversion on offer, every
# input of the conversion decision pinned. Read by
# tests/end_to_end/test_fuel_price_response.py.
Fleet "container_15000_teu" {
	RetrofitInterval = 5                   # years
	MinimumConversionAge = 5            # years
	ConversionSensitivity = 2

	set_conversion_cost("container_15000_teu_ice_oil", "container_15000_teu_ice_methane", 10e6)  # USD
}
