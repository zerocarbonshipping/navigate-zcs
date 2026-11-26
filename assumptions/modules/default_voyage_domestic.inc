# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "*domestic*" {
    set_distance_share("*", "*", 0)
	set_distance_share("port_global", "port_global", Variable("voyage_domestic_global"))
	set_distance_share("port_europe", "port_europe", Variable("voyage_domestic_europe"))
}
