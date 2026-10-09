# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Two propulsion-saving technologies, installed on every vessel of the base
# fleet from the start: the initial share is 1 at every age, so the fleet's
# full package is the one in use. The %name% values are filled in by
# tests/end_to_end/test_technology_combinations.py: the list of technologies
# the fleet offers, and the saving of each.
Technology "combination_technology_a" {
	set_energy_saving(PROPULSION, %saving_a%)
}

Technology "combination_technology_b" {
	set_energy_saving(PROPULSION, %saving_b%)
}

Curve "combination_full_uptake" {
	Table = [
		0	1
		100	1
	]
}

Fleet "container_15000_teu" {
	Technologies = [%technologies%]
	set_initial_technology_share("*", "combination_technology_*", Curve("combination_full_uptake"))
}
