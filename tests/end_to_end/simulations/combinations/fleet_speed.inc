# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the base fleet with the speed settings under test. The %name%
# values are filled in by tests/end_to_end/test_route_speed_combinations.py.
Fleet "container_15000_teu" {
	AllowSpeedManagement = %allow_speed_management%
	SpeedAlignment = %speed_alignment%
}
