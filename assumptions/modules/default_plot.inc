# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: CC-BY-4.0

Plot "plots" {
	Directory = "./plots/"

	add_plot("engine_fuel_consumed")
	add_plot("fuel_type_supply_demand")
	add_plot("global_emission_absolute")
	add_plot("global_fuel_consumed")
	add_plot("global_energy_saving")
	add_plot("global_installed_power")
	add_plot("producer_development")
	add_plot("regulation_compliance")
	add_plot("regulation_flexibility_cost")
}

Plot "plots_analysis" {
	Directory = "./plots_analysis/"

	add_plot("engine_age")
	add_plot("engine_pilot_fuel_share")
	add_plot("fleet_emission_absolute")
	add_plot("fleet_emission_intensity")
	add_plot("fleet_fuel_consumed")
	add_plot("fleet_conversions_cumulative")
	add_plot("fleet_evolution")
	add_plot("fleet_changes")
	add_plot("fleet_energy_saving")
	add_plot("fleet_investment_metric")
	add_plot("fleet_shore_power_share")
	add_plot("fleet_speed")
	add_plot("fleet_speed_per_vessel")
	add_plot("fuel_supply_demand")
	add_plot("global_emission_intensity")
	add_plot("global_energy_demand")
	add_plot("global_shore_power_share")
	add_plot("global_fuel_type_consumed")
	add_plot("global_feedstock_consumption")
	add_plot("global_fuel_related_expenses")
	add_plot("global_fuel_related_expenses_cumulative")
	add_plot("global_expenses")
	add_plot("global_expenses_cumulative")
	add_plot("global_tied_capital")
	add_plot("global_installed_power_share")
	add_plot("global_power_converted_cumulative")
	add_plot("producer_feed_consumption")
	add_plot("plant_production_cost")
	add_plot("plant_production_emissions")
	add_plot("port_bunker_price")
	add_plot("port_bunker_supply")
	add_plot("producer_development_cumulative")
}
