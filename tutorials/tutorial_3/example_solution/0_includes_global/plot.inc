# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

# Definition of the plots produced for each scenario.
# Directory points at the "plots" subfolder of the scenario; each add_plot(...)
# selects one plot to produce.

Plot "plots" {
	Directory = "./plots/"

	add_plot("global_emission_absolute")
	add_plot("global_fuel_consumed")
	add_plot("plant_production_cost")
	add_plot("port_bunker_price")
}
