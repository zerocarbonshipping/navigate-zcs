# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plot "plots_debug" {
	Directory = "./plots_debug/"

	add_plot("computational_performance")
	add_plot("computational_performance_cumulative")
	add_plot("fleet_newbuild_sources")
	add_plot("fleet_fuel_conversion_sources")
	add_plot("fleet_trade")
	add_plot("fleet_investment_signal_technology_per_vessel")
	add_plot("fleet_investment_signal_speed_per_vessel")
	add_plot("fuel_supply_demand_expectation")
	add_plot("producer_changes")
	add_plot("producer_fair_share")
	add_plot("regulation_flexibility")
	add_plot("technology_uptake")
	add_plot("technology_install_sources")
}
