<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Plot

A `Plot` node defines which plots are generated from the simulation results and where they are
saved. Plots are only produced when at least one `Plot` node is defined (and plotting is not
suppressed with the `-s` flag).

Example:

```python
Plot "plots" {
    Directory = "./plots/"

    add_plot("global_emission_absolute")
    add_plot("global_fuel_consumed")
    add_plot("port_bunker_price")
}
```

## Attributes

### Directory

This attribute defines the directory in which the plots are stored, relative to the `.nav` file.
The folder is created automatically if it does not already exist.

* **Data type**: `String`
* Format: Must be a valid directory readable by the Python 'os' module.
* **Default**: A `plots` folder next to the `.nav` file

## Commands

### add\_plot

This command selects a single plot to be produced, by its label. Call it once per plot. If no
`add_plot` command is given, every available plot is produced.

The label must be given as a quoted string, e.g. `add_plot("global_fuel_consumed")`.

* Label: All available plot labels are listed in the [Plot Labels](#appendix---plot-node-labels) section.

## Appendix - Plot Node Labels

The labels below are the values accepted by the `add_plot` command on a `Plot` node. Each label must be passed as a quoted string, e.g. `add_plot("global_fuel_consumed")`.

| **Plot label**                                  | **Category**               |
|-------------------------------------------------|----------------------------|
| global_emission_absolute                        | Global                     |
| global_emission_intensity                       | Global                     |
| global_fuel_consumed                            | Global                     |
| global_energy_demand                            | Global                     |
| global_fuel_type_consumed                       | Global                     |
| global_shore_power_share                        | Global                     |
| global_feedstock_consumption                    | Global                     |
| global_fuel_related_expenses                    | Global                     |
| global_fuel_related_expenses_cumulative         | Global                     |
| global_expenses                                 | Global                     |
| global_expenses_cumulative                      | Global                     |
| global_tied_capital                             | Global                     |
| global_energy_saving                            | Global                     |
| global_installed_power                          | Global                     |
| global_installed_power_share                    | Global                     |
| global_power_converted_cumulative               | Global                     |
| engine_fuel_consumed                            | Engine                     |
| engine_age                                      | Engine                     |
| engine_pilot_fuel_share                         | Engine                     |
| fuel_supply_demand                              | Fuel                       |
| fuel_supply_demand_expectation                  | Fuel                       |
| fuel_type_supply_demand                         | Fuel                       |
| fleet_emission_absolute                         | Fleet                      |
| fleet_emission_intensity                        | Fleet                      |
| fleet_fuel_consumed                             | Fleet                      |
| fleet_shore_power_share                         | Fleet                      |
| fleet_conversions_cumulative                    | Fleet                      |
| fleet_evolution                                 | Fleet                      |
| fleet_orderbook                                 | Fleet                      |
| fleet_changes                                   | Fleet                      |
| fleet_energy_saving                             | Fleet                      |
| fleet_trade                                     | Fleet                      |
| fleet_speed                                     | Fleet                      |
| fleet_speed_per_vessel                          | Fleet                      |
| fleet_investment_metric                         | Fleet                      |
| fleet_investment_signal_technology_per_vessel   | Fleet                      |
| fleet_investment_signal_speed_per_vessel        | Fleet                      |
| fleet_newbuild_sources                          | Fleet                      |
| fleet_fuel_conversion_sources                   | Fleet                      |
| fleet_fuel_conversion_sources_normalized        | Fleet                      |
| producer_development                            | Producer                   |
| producer_development_cumulative                 | Producer                   |
| producer_feed_consumption                       | Producer                   |
| producer_fair_share                             | Producer                   |
| plant_production_cost                           | Plant                      |
| plant_production_emissions                      | Plant                      |
| port_bunker_price                               | Port                       |
| port_bunker_supply                              | Port                       |
| technology_uptake                               | Technology                 |
| technology_install_sources                      | Technology                 |
| technology_install_sources_normalized           | Technology                 |
| regulation_compliance                           | Regulation                 |
| regulation_flexibility                          | Regulation                 |
| regulation_unit_trading                         | Regulation                 |
| regulation_flexibility_cost                     | Regulation                 |
| regulation_offsetting_units                     | Regulation                 |
| regulation_offsetting_expenses                  | Regulation                 |
| regulation_offsetting_cost                      | Regulation                 |
| computational_performance                       | Computational performance  |
| computational_performance_cumulative            | Computational performance  |
