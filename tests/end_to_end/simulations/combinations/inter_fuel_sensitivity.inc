# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the base fleet with the newbuild fuel-choice sensitivity under test.
# The %name% value is filled in by tests/end_to_end/test_calibration_direction.py.
Fleet "container_15000_teu" {
	InterFuelSensitivity = %sensitivity%
}
