# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "ammonia_synthesis_electro_alkaline" {
	Feeds = [Process("hydrogen_electro_alkaline"), Process("nitrogen_air_separation")]
	Conversions = [Variable("ammonia_hydrogen_conversion"), Variable("ammonia_nitrogen_conversion")]
}
