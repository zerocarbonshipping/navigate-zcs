# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Process "electrolysis_stack_pem" {
	Feeds = [Feedstock("demineralized_water")]
	Conversions = [Variable("hydrogen_demineralized_water_conversion")]
}
