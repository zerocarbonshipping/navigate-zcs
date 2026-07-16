# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# ------------------------------- EXPORT --------------------------------------
#
# This file defines the attributes from the example that are
# exported to an excel file.
#
# ---------------------------------------------------------------------------

Report "output" {
	Directory = "./plots"
	
	add_port_property("*", BunkerIntensityPrice)
}
