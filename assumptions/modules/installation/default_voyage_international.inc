# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Route "*international*" {

    set_voyage_distribution("*", "*", 0)

	# intra
	set_voyage_distribution("port_europe", "port_europe", Variable("voyage_international_europe_intra"))

	# Europe (incoming)
	set_voyage_distribution("port_global", "port_europe", Variable("voyage_international_europe_incoming"))

	# Europe (outgoing)
	set_voyage_distribution("port_europe", "port_global", Variable("voyage_international_europe_outgoing"))

	# remaining (intra + rest)
	set_voyage_distribution("port_global", "port_global", Variable("voyage_international_global"))
}
