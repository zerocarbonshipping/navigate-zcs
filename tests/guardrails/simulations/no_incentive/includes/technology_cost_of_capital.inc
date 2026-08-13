# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# Pinned discount rate for technology-investment NPVs: the installation
# defaults leave TechnologyCostOfCapital unset, in which case the model
# falls back to the vessel cost of capital and warns that this inflates
# technology uptake. Included after Load DefaultCalibration so the pin
# survives even if the calibration module ever sets this attribute too.
Fleet "*" {
	TechnologyCostOfCapital = 0.08
}
