# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit of every series attribute in the results file.

The results file names a series by its profile reader with a leading ``get_``
stripped (``get_consumed_energy`` -> ``consumed_energy``); this table maps each such
attribute to the unit its values are in, so a viewer can label the axes. The table
covers the readers of every profile class, including the ones a class inherits from
the private base profiles, and tests/unit/output/test_result_units.py keeps it in
step with them.

The unit strings are plain ASCII without metric prefixes:

* rates are per year (``GJ/year``, ``t/year``, ``USD/year``); a ``cumulative_``
  reader integrates its rate over the timeline and drops the ``/year``;
* ``t`` is the metric ton; ``tCO2e`` is a ton of CO2-equivalent, weighted by the
  global warming potential (the model's own, or a policy's for regulation and levy
  units), while a bare ``t`` of emission is one gas unweighted;
* emission intensities are ``g/MJ`` (equal to kg/GJ): the profiles divide tons by GJ
  and scale by 10^3;
* a cargo-mile is one unit of cargo carried one nautical mile, where the cargo unit
  is the vessel segment's own (TEU, CEU, dwt, ...) and matches the fleet's trade;
* ``-`` marks a dimensionless fraction, share or flag;
* ``measure`` marks a value in the unit of the regulation's measure: tCO2e/year
  for ABSOLUTE, gCO2e/MJ for INTENSITY, gCO2e/cargo-mile for TRANSPORT and
  gCO2e/nominal cargo-mile for TRANSPORT_NOMINAL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

UNITS: Final[Mapping[str, str]] = {
    # energy demand ------------------------------------------------------------------
    "raw_energy": "GJ/year",
    "raw_energy_port": "GJ/year",
    "raw_energy_sea": "GJ/year",
    "operational_energy": "GJ/year",
    "operational_energy_port": "GJ/year",
    "operational_energy_sea": "GJ/year",
    "energy": "GJ/year",
    "energy_port": "GJ/year",
    "energy_sea": "GJ/year",
    "total_energy_port": "GJ/year",
    "baseline_energy": "GJ/year",
    # energy savings, relative to a reference demand ---------------------------------
    "saving": "-",
    "energy_intensity_saving": "-",
    "operational_energy_intensity_saving": "-",
    "speed_energy_intensity_saving": "-",
    "technology_energy_intensity_saving": "-",
    "energy_saving": "-",
    "operational_energy_saving": "-",
    "speed_energy_saving": "-",
    "technology_energy_saving": "-",
    # fuel consumed ------------------------------------------------------------------
    "consumed_energy": "GJ/year",
    "converter_energy": "GJ/year",
    "fuel_type_energy": "GJ/year",
    "total_consumed_energy": "GJ/year",
    "fuel_type_demand": "GJ/year",
    "pilot_fuel_share": "-",
    # shore power --------------------------------------------------------------------
    "shore_power_energy": "GJ/year",
    "shore_power_expenses": "USD/year",
    # one gas, unweighted: the shore-power factors are ton per GJ supplied
    "shore_power_emission": "t/year",
    # emissions of a fuel consumer ---------------------------------------------------
    "equivalent_ttw": "tCO2e/year",
    "equivalent_wtt": "tCO2e/year",
    "equivalent_wtw": "tCO2e/year",
    "total_equivalent_ttw": "tCO2e/year",
    "total_equivalent_wtt": "tCO2e/year",
    "total_equivalent_wtw": "tCO2e/year",
    "cumulative_equivalent_ttw": "tCO2e",
    "cumulative_equivalent_wtt": "tCO2e",
    "cumulative_equivalent_wtw": "tCO2e",
    "cumulative_total_equivalent_ttw": "tCO2e",
    "cumulative_total_equivalent_wtt": "tCO2e",
    "cumulative_total_equivalent_wtw": "tCO2e",
    # per total consumed energy
    "intensity_equivalent_ttw": "gCO2e/MJ",
    "intensity_equivalent_wtt": "gCO2e/MJ",
    "intensity_equivalent_wtw": "gCO2e/MJ",
    "intensity_total_equivalent_ttw": "gCO2e/MJ",
    "intensity_total_equivalent_wtt": "gCO2e/MJ",
    "intensity_total_equivalent_wtw": "gCO2e/MJ",
    # expenses of a fuel consumer ----------------------------------------------------
    "fuel_expenses": "USD/year",
    "levy_expenses": "USD/year",
    "fuel_related_expenses": "USD/year",
    "total_fuel_expenses": "USD/year",
    "total_levy_expenses": "USD/year",
    "total_fuel_related_expenses": "USD/year",
    "regulation_expenses": "USD/year",
    "cumulative_fuel_expenses": "USD",
    "cumulative_levy_expenses": "USD",
    "cumulative_fuel_related_expenses": "USD",
    "cumulative_total_fuel_expenses": "USD",
    "cumulative_total_levy_expenses": "USD",
    "cumulative_total_fuel_related_expenses": "USD",
    "cumulative_flexibility_expenses": "USD",
    "cumulative_remedial_expenses": "USD",
    "cumulative_surplus_revenue": "USD",
    "cumulative_regulation_expenses": "USD",
    # levy units are the levy collected over its level (USD/tCO2e), so CO2-equivalent
    # under the levy's GWP
    "levy_units": "tCO2e/year",
    # shared by the fuel consumers (per regulation) and the regulation itself
    "flexibility_expenses": "USD/year",
    "remedial_expenses": "USD/year",
    "surplus_revenue": "USD/year",
    "remedial_units": "tCO2e/year",
    # vessel aggregates: power, turnover and vessel expenses -------------------------
    "installed_power": "MW",
    "newbuild_power": "MW/year",
    "scrapped_power": "MW/year",
    "fuel_converted_power": "MW/year",
    "cumulative_newbuild_power": "MW",
    "cumulative_scrapped_power": "MW",
    "cumulative_fuel_converted_power": "MW",
    "weighted_average_age": "years",
    "vessel_expenses": "USD/year",
    "technology_expenses": "USD/year",
    "fuel_conversion_expenses": "USD/year",
    "vessel_related_expenses": "USD/year",
    "expenses": "USD/year",
    "cumulative_vessel_expenses": "USD",
    "cumulative_technology_expenses": "USD",
    "cumulative_fuel_conversion_expenses": "USD",
    "cumulative_vessel_related_expenses": "USD",
    "cumulative_expenses": "USD",
    # capital tied up, a stock rather than a rate
    "vessel_tied_capital": "USD",
    "plant_tied_capital": "USD",
    # fleet: trade, composition and technology uptake --------------------------------
    "trade": "cargo-miles/year",
    "cargo_miles": "cargo-miles/year",
    "existing_vessels": "vessels",
    "newbuilds": "vessels/year",
    "scrap": "vessels/year",
    "fuel_conversions": "vessels/year",
    "technology_uptake": "-",
    "fleet_technology_uptake": "-",
    "newbuild_technology_uptake": "-",
    "retrofit_technology_uptake": "-",
    # speeds (fleet and vessel) ------------------------------------------------------
    "reference_speed": "knots",
    "minimum_speed": "knots",
    "maximum_speed": "knots",
    "actual_speed": "knots",
    "optimal_speed": "knots",
    "lowest_speed": "knots",
    "highest_speed": "knots",
    # vessel: economics and state ----------------------------------------------------
    "lifetime": "years",
    "lead_time": "years",
    "asset_charter_rate": "USD/year",
    "cargo_charter_rate": "USD/year",
    "technology_cost": "USD/year",
    "investment_freight_rate": "USD/cargo-mile",
    "instantaneous_freight_rate": "USD/cargo-mile",
    "investment_signal_speed": "USD/GJ",
    "investment_signal_technology": "USD/GJ",
    "is_active": "-",
    "is_in_fleet": "-",
    "cost_is_calculated": "-",
    # fuel production ----------------------------------------------------------------
    "production_energy": "GJ/year",
    "production_type_energy": "GJ/year",
    "feed_mass": "t/year",
    "feed_constraint": "t/year",
    # producer -----------------------------------------------------------------------
    "development": "plants/year",
    "maximum_development": "plants/year",
    "cumulative_development": "plants",
    "cumulative_maximum_development": "plants",
    "fair_share_fuel_fraction": "-",
    # plant: cost and well-to-tank emissions of the fuel it makes ---------------------
    "investment_cost": "USD/t",
    "instantaneous_cost": "USD/t",
    "investment_intensity_cost": "USD/GJ",
    "instantaneous_intensity_cost": "USD/GJ",
    # per ton of fuel produced
    "equivalent_investment_wtt": "tCO2e/t",
    "equivalent_instantaneous_wtt": "tCO2e/t",
    "total_equivalent_investment_wtt": "tCO2e/t",
    "total_equivalent_instantaneous_wtt": "tCO2e/t",
    # per energy in the fuel produced
    "intensity_equivalent_investment_wtt": "gCO2e/MJ",
    "intensity_equivalent_instantaneous_wtt": "gCO2e/MJ",
    "intensity_total_equivalent_investment_wtt": "gCO2e/MJ",
    "intensity_total_equivalent_instantaneous_wtt": "gCO2e/MJ",
    # bunkering infrastructure (port and manager) ------------------------------------
    "bunker_mass": "t/year",
    "bunker_energy": "GJ/year",
    "bunker_supply_mass": "t/year",
    "bunker_supply_energy": "GJ/year",
    "bunkering_limit_mass": "t/year",
    "bunkering_limit_energy": "GJ/year",
    # port: bunker permission, price and well-to-tank emissions ----------------------
    "bunkering_allowed": "-",
    "bunker_price": "USD/t",
    "bunker_intensity_price": "USD/GJ",
    # one gas, unweighted, per ton of fuel bunkered
    "bunker_wtt": "t/t",
    "equivalent_bunker_wtt": "tCO2e/t",
    "total_equivalent_bunker_wtt": "tCO2e/t",
    # per energy in the fuel bunkered
    "bunker_intensity_wtt": "g/MJ",
    "bunker_intensity_equivalent_wtt": "gCO2e/MJ",
    "bunker_intensity_total_equivalent_wtt": "gCO2e/MJ",
    # regulation ---------------------------------------------------------------------
    # thresholds and compliance are in the measure unit of the regulation
    "vessel_threshold": "measure",
    "shared_threshold": "measure",
    "adjusted_vessel_threshold": "measure",
    "adjusted_shared_threshold": "measure",
    "vessel_compliance": "measure",
    "shared_compliance": "measure",
    # the absolute emissions behind the measure, CO2-equivalent under the
    # regulation's GWP, whatever the measure
    "vessel_allowance": "tCO2e/year",
    "shared_allowance": "tCO2e/year",
    "vessel_units": "tCO2e/year",
    "shared_units": "tCO2e/year",
    "surplus_units": "tCO2e/year",
    "flexibility_units": "tCO2e/year",
    "non_compliance_units": "tCO2e/year",
    # cost of one compliance unit
    "remedial_cost": "USD/tCO2e",
    "flexibility_cost": "USD/tCO2e",
    # levy ---------------------------------------------------------------------------
    # revenue collected, negative where the levy pays out a subsidy
    "collected": "USD/year",
    # computational timings of the run (manager) -------------------------------------
    "total_time": "s",
    "expected_build_time": "s",
    "expected_solve_time": "s",
    "expected_transfer_time": "s",
    "existing_build_time": "s",
    "existing_solve_time": "s",
    "existing_transfer_time": "s",
    "speed_time": "s",
    "retrofit_time": "s",
    "fleet_evolution_time": "s",
    "producer_evolution_time": "s",
    "temporal_time": "s",
    "vessel_time": "s",
    "fuel_supply_time": "s",
    "policy_time": "s",
    "fleet_state_time": "s",
    "profile_agg_time": "s",
    "overhead_time": "s",
}
