# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Single source of truth for which plots :func:`render_plots` renders.

``PLOTS`` is the ordered catalogue of every rendered plot. A plot's label
(used by ``selected_plots`` and warnings) is its function name without the
``plot_`` prefix -- see :func:`plot_label` -- so there is no separate list of
labels to keep in sync. To add a plot, import it and append it to ``PLOTS``.
"""

from navigate.illustrations.plots.computational_performance import (
    plot_computational_performance,
    plot_computational_performance_cumulative,
)
from navigate.illustrations.plots.engine_age import plot_engine_age
from navigate.illustrations.plots.engine_fuel_consumed import plot_engine_fuel_consumed
from navigate.illustrations.plots.engine_pilot_fuel_share import plot_engine_pilot_fuel_share
from navigate.illustrations.plots.fleet_changes import plot_fleet_changes
from navigate.illustrations.plots.fleet_conversions import plot_fleet_conversions_cumulative
from navigate.illustrations.plots.fleet_emission_absolute import plot_fleet_emission_absolute
from navigate.illustrations.plots.fleet_emission_intensity import plot_fleet_emission_intensity
from navigate.illustrations.plots.fleet_energy_saving import plot_fleet_energy_saving
from navigate.illustrations.plots.fleet_evolution import plot_fleet_evolution
from navigate.illustrations.plots.fleet_fuel_consumed import plot_fleet_fuel_consumed
from navigate.illustrations.plots.fleet_investment_metric import plot_fleet_investment_metric
from navigate.illustrations.plots.fleet_investment_signal_per_vessel import (
    plot_fleet_investment_signal_speed_per_vessel,
    plot_fleet_investment_signal_technology_per_vessel,
)
from navigate.illustrations.plots.fleet_shore_power_share import plot_fleet_shore_power_share
from navigate.illustrations.plots.fleet_speed import plot_fleet_speed
from navigate.illustrations.plots.fleet_speed_per_vessel import plot_fleet_speed_per_vessel
from navigate.illustrations.plots.fleet_trade import plot_fleet_trade
from navigate.illustrations.plots.fuel_supply_demand import plot_fuel_supply_demand
from navigate.illustrations.plots.fuel_type_supply_demand import plot_fuel_type_supply_demand
from navigate.illustrations.plots.global_emission_absolute import plot_global_emission_absolute
from navigate.illustrations.plots.global_emission_intensity import plot_global_emission_intensity
from navigate.illustrations.plots.global_energy_demand import plot_global_energy_demand
from navigate.illustrations.plots.global_energy_saving import plot_global_energy_saving
from navigate.illustrations.plots.global_expenses import plot_global_expenses, plot_global_expenses_cumulative
from navigate.illustrations.plots.global_feedstock_consumption import plot_global_feedstock_consumption
from navigate.illustrations.plots.global_fuel_consumed import plot_global_fuel_consumed
from navigate.illustrations.plots.global_fuel_related_expenses import (
    plot_global_fuel_related_expenses,
    plot_global_fuel_related_expenses_cumulative,
)
from navigate.illustrations.plots.global_fuel_type_consumed import plot_global_fuel_type_consumed
from navigate.illustrations.plots.global_installed_power import plot_global_installed_power
from navigate.illustrations.plots.global_installed_power_share import plot_global_installed_power_share
from navigate.illustrations.plots.global_power_converted import plot_global_power_converted_cumulative
from navigate.illustrations.plots.global_shore_power_share import plot_global_shore_power_share
from navigate.illustrations.plots.global_tied_capital import plot_global_tied_capital
from navigate.illustrations.plots.plant_production_cost import plot_plant_production_cost
from navigate.illustrations.plots.plant_production_emissions import plot_plant_production_emissions
from navigate.illustrations.plots.port_bunker_price import plot_port_bunker_price
from navigate.illustrations.plots.port_bunker_supply import plot_port_bunker_supply
from navigate.illustrations.plots.producer_development import (
    plot_producer_development,
    plot_producer_development_cumulative,
)
from navigate.illustrations.plots.producer_fair_share import plot_producer_fair_share
from navigate.illustrations.plots.producer_feed_consumption import plot_producer_feed_consumption
from navigate.illustrations.plots.regulation_compliance import plot_regulation_compliance
from navigate.illustrations.plots.regulation_flexibility import plot_regulation_flexibility
from navigate.illustrations.plots.regulation_flexibility_cost import plot_regulation_flexibility_cost
from navigate.illustrations.plots.regulation_unit_trading import plot_regulation_unit_trading
from navigate.illustrations.plots.technology_uptake import plot_technology_uptake

PLOTS = [
    plot_global_emission_absolute,
    plot_global_emission_intensity,
    plot_global_fuel_consumed,
    plot_global_energy_demand,
    plot_global_fuel_type_consumed,
    plot_global_shore_power_share,
    plot_global_feedstock_consumption,
    plot_global_fuel_related_expenses,
    plot_global_fuel_related_expenses_cumulative,
    plot_global_expenses,
    plot_global_expenses_cumulative,
    plot_global_tied_capital,
    plot_global_energy_saving,
    plot_global_installed_power,
    plot_global_installed_power_share,
    plot_global_power_converted_cumulative,
    plot_engine_fuel_consumed,
    plot_engine_age,
    plot_engine_pilot_fuel_share,
    plot_fuel_supply_demand,
    plot_fuel_type_supply_demand,
    plot_fleet_emission_absolute,
    plot_fleet_emission_intensity,
    plot_fleet_fuel_consumed,
    plot_fleet_shore_power_share,
    plot_fleet_conversions_cumulative,
    plot_fleet_evolution,
    plot_fleet_changes,
    plot_fleet_energy_saving,
    plot_fleet_speed,
    plot_fleet_speed_per_vessel,
    plot_fleet_investment_signal_technology_per_vessel,
    plot_fleet_investment_signal_speed_per_vessel,
    plot_fleet_trade,
    plot_fleet_investment_metric,
    plot_producer_development,
    plot_producer_development_cumulative,
    plot_producer_feed_consumption,
    plot_producer_fair_share,
    plot_plant_production_cost,
    plot_plant_production_emissions,
    plot_port_bunker_price,
    plot_port_bunker_supply,
    plot_technology_uptake,
    plot_regulation_compliance,
    plot_regulation_flexibility,
    plot_regulation_unit_trading,
    plot_regulation_flexibility_cost,
    plot_computational_performance,
    plot_computational_performance_cumulative,
]


def plot_label(func):
    """Return a plot function's label (its name without the ``plot_`` prefix)."""
    return func.__name__[len('plot_'):]


PLOT_LABELS = frozenset(plot_label(f) for f in PLOTS)
