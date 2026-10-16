# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the fleet of fuel_conversion.inc with the conversion sensitivity
# under test. The %name% value is filled in by
# tests/end_to_end/test_calibration_direction.py.
Fleet "container_15000_teu" {
	FuelConversionSensitivity = %sensitivity%
}
