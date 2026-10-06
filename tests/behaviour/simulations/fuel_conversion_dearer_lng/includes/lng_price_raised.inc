# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# The perturbation: LNG raised from 380 to 480 USD/ton, still below oil's
# 550, so conversion keeps a business case but a smaller one.
Port "*" {
	set_bunker_price_overwrite("liquefied_natural_gas", 480)    # USD/ton
}
