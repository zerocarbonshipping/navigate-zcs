# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of Producer

Producer "engineering_procurement_construction" {
	Plants = [Plant("plant_methane_electro"), Plant("plant_methanol_bio_gasification"), Plant("plant_ammonia_blue")]
	FuelDemandSensitivity = 1.5
	FuelCostSensitivity = 0.5

	MaximumDevelopment = 10
}
