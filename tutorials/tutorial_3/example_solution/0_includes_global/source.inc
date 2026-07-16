# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of vessel finance

#Source of electricity for production of fuels
Source "renewable" {
	Dependency = CONNECTED
}

Source "grid" {  #blue and bio fuels sources electricity from the grid in the region where it is being produced.
	Dependency = CONNECTED
}
