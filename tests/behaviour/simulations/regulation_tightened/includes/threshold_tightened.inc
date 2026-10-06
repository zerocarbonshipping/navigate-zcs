# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# The perturbation: the threshold trajectory scaled by 0.8 at every step
# (93.3 x 0.8 gCO2e/MJ baseline), so each step allows less WTW intensity.
Forecast "intensity_target_reduction" {
	Multiplier = 74.64
}
