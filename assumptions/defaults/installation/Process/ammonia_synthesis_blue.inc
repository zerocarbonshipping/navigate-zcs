# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "ammonia_synthesis_blue" {
	Feeds = [Process("autothermal_reforming"), Process("nitrogen_air_separation")]
	Conversions = [Variable("ammonia_hydrogen_conversion"), Variable("ammonia_nitrogen_conversion")]
}
