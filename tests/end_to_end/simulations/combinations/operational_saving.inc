# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Re-opens the base fleet with an operational saving on every energy demand its
# vessels have: propulsion and electrical at sea, electrical in port. They have
# no heat demand, so a HEAT saving would have nothing to act on. The %name%
# values are filled in by tests/end_to_end/test_technology_combinations.py, one
# distinct value per demand, so a saving applied to the wrong demand shows up
# as a wrong ratio.
Fleet "container_15000_teu" {
	set_operational_saving_sea(PROPULSION, %sea_propulsion%)
	set_operational_saving_sea(ELECTRICAL, %sea_electrical%)

	set_operational_saving_port(ELECTRICAL, %port_electrical%)
}
