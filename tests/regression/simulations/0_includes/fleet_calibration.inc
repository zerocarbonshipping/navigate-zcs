# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Pinned fleet decision-process calibration shared by the regression decks
# (rounded from the 2026-09-14 installation defaults): pinned so upstream
# calibration changes cannot silently re-size the scenarios, shared so the
# decks cannot drift apart. Included after the deck's fleet include, which
# defines the fleet this re-opens.
Fleet "container_15000_teu" {
	Inertia = 0.0
	InterFuelSensitivity = 0.75
	IntraFuelSensitivity = 0.75
	FuelConversionSensitivity = 2
	TechnologySensitivity = 2
}
