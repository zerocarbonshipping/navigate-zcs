# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "hydrogen_electro_soec" {
	Feeds = [Process("electrolysis_stack_soec")]
	Conversions = [1]
}
