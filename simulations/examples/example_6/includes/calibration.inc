# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# DECISION PROCESSES - the Port and Fleet blocks of the library's DefaultCalibration
# (assumptions/modules/installation/default_calibration.inc), restated because the
# deck has no Producer for its Producer "*" block to match.

Port "*" {
	set_bunkering_inertia("*", 0.7)
}

Fleet "*" {
	Inertia = 0.6
	InterFuelSensitivity = 0.75
	IntraFuelSensitivity = 0.75
	FuelConversionSensitivity = 2
	TechnologySensitivity = 2
}
