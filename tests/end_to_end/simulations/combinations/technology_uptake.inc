# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# One propulsion-saving technology the base fleet may install on newbuilds and
# by retrofit, none of it installed at the start, every input of its business
# case pinned. The %name% value is filled in by
# tests/end_to_end/test_technology_combinations.py.
Technology "combination_technology" {
	set_energy_saving(PROPULSION, 0.05)

	Capex = %capex%                     # USD
	Opex = 0                            # USD/year
	Lifetime = 25                       # years
}

Fleet "container_15000_teu" {
	Technologies = [Technology("combination_technology")]

	TechnologyCostOfCapital = 0.08
	RetrofitFrequency = 5               # years
}
