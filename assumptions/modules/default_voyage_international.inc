# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "*international*" {

    set_distance_share("*", "*", 0)

	# intra
	set_distance_share("port_europe", "port_europe", Variable("voyage_international_europe_intra"))

	# Europe (incoming)
	set_distance_share("port_global", "port_europe", Variable("voyage_international_europe_incoming"))

	# Europe (outgoing)
	set_distance_share("port_europe", "port_global", Variable("voyage_international_europe_outgoing"))

	# remaining (intra + rest)
	set_distance_share("port_global", "port_global", Variable("voyage_international_global"))
}
