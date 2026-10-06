# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# The perturbation: the levy level scaled to zero at every step. The Levy
# node stays in the deck, so only its price signal is removed.
Forecast "carbon_levy_level" {
	Multiplier = 0
}
