# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the producer of 0_includes/supply_chain.inc with the plant-split
# sensitivity under test. The %name% value is filled in by
# tests/end_to_end/test_calibration_direction.py.
Producer "epc_ammonia" {
	FuelCostSensitivity = %sensitivity%
}
