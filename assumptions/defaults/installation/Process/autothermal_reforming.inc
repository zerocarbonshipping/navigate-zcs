# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "autothermal_reforming" {
	Feeds = [Feedstock("natural_gas")]
	Conversions = [Variable("autothermal_reforming_natural_gas_conversion")]
}
