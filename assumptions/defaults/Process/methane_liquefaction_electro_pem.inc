# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "methane_liquefaction_electro_pem" {
	Feeds = [Process("methane_synthesis_electro_pem")]
	Conversions = [1]
}
