# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The model's time stepping: Simulation steps the nodes of a read deck through its dates.

navigate.driver runs it: initialized once, stepped at each date once the date's events
are applied, and finished into the global results; each node holds its own.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core import define_vessel_fuel_maps, update_imposed_levies
from navigate.core.enum_ import BunkerScopeID, TimingID
from navigate.core.results import GlobalResults, ResultsContext
from navigate.exceptions import DeckError
from navigate.simulation.bunker import BunkerAlgorithm, calculate_fair_share_fuel_supply
from navigate.simulation.bunker.solver import set_solver_preference
from navigate.simulation.fleet import (
    approximate_missing_technology,
    assign_vessels_to_fleets,
    calculate_asset_charter,
    calculate_cargo_charter,
    calculate_fleet_evolution_expectation,
    calculate_fleet_expectations,
    calculate_fleet_fuel_demand,
    calculate_fuel_type_balance,
    calculate_potential_fuel_type_demand,
    calculate_shore_power_limits,
    check_fuel_options,
    close_trade_gap,
    complete_fleet_results,
    complete_global_fleet_results,
    complete_vessel_results,
    determine_fuel_type,
    initialize_existing_fleet,
    perform_fuel_conversions,
    perform_primary_scrapping,
    perform_speed_management,
    perform_technology_installation,
    record_fleet_results,
    record_investment_signals,
    record_vessel_results,
    transfer_technology_charter_rate,
    update_operations,
    update_residual_energy_demand,
    update_vessel_ages,
    update_vessel_scarcity_beliefs,
    verify_power_capacity,
)
from navigate.simulation.fuel import (
    calculate_development_potential,
    calculate_expected_fuel_demand,
    calculate_expected_fuel_gap,
    calculate_expected_fuel_supply,
    calculate_export_expectations,
    calculate_fair_share_demand,
    calculate_feed_availability,
    calculate_fuel_import_to_ports,
    calculate_plant_logistics_expectations,
    calculate_plant_production_expectations,
    calculate_port_expectations,
    calculate_producer_evolution_expectation,
    complete_global_fuel_results,
    complete_plant_results,
    complete_port_results,
    complete_producer_results,
    initialize_existing_producer,
    perform_decommissioning,
    perform_pipeline_delivery,
    perform_pipeline_planning,
    record_plant_results,
    record_port_results,
    record_producer_results,
    update_plant_ages,
)
from navigate.simulation.policy import (
    calculate_adjusted_regulation_thresholds,
    calculate_flexibility_markets,
    calculate_individual_remedial_expenses,
    calculate_policy_emission_coefficients,
    calculate_policy_expectations,
    calculate_regulation_bunkering_inputs,
    calculate_regulation_compliance,
    calculate_regulation_measures,
    complete_regulation_results,
    record_regulation_results,
    update_regulation_flexibility_beliefs,
)
from navigate.util import YEAR, Timings, dates_to_days, timed, timedelta_to_days

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np

    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.util.types_ import DateArray, FloatArray

logger = logging.getLogger(__name__)


def check_runnable(nodes: Nodes) -> None:
    """
    Raise where a read deck defines no Fleet or no Fuel to simulate.

    Parameters
    ----------
    nodes
        The node registry of the read deck.
    """
    # a Fleet requires Vessels, a Vessel a Route, a Route Ports; emissions may be absent
    missing = [
        label
        for registry, label in ((nodes.fleets, "Fleets"), (nodes.fuels, "Fuels"))
        if not registry
    ]
    if missing:
        listed = "".join(f"\t- No {label} are defined.\n" for label in missing)
        raise DeckError(f"Unable to run a simulation:\n{listed}")


class Simulation:
    """
    Step the nodes of a read deck through its dates, from initial conditions to results.

    Parameters
    ----------
    nodes
        Nodes of the deck.
    general_nodes
        General nodes of the deck.
    dateline
        Dates of the simulation timeline, the start date first.
    output_directory
        Folder the bunkering LP writes an infeasible model into.
    """

    def __init__(
        self,
        nodes: Nodes,
        general_nodes: GeneralNodes,
        dateline: DateArray,
        output_directory: Path,
    ) -> None:
        check_runnable(nodes)

        self.nodes: Nodes = nodes
        self.general_nodes: GeneralNodes = general_nodes
        self._output_directory: Path = output_directory

        # properties -------------------------------------------------------------------
        # the current time-step size and elapsed simulation time, in days
        self._time_step: float = 0.0
        self._time: float = 0.0
        self._date: np.datetime64 = dateline[0]
        self._idx: int = 0

        # the simulation's dates, and the elapsed time in days since the start date
        self.dateline: DateArray = dateline
        self.timeline: FloatArray = dates_to_days(self.dateline)

        # results
        self.global_results: GlobalResults = GlobalResults()

        # bunker algorithm -------------------------------------------------------------
        self._bunker_existing: BunkerAlgorithm = BunkerAlgorithm()
        self._bunker_expected: BunkerAlgorithm = BunkerAlgorithm()

        # computational time -----------------------------------------------------------
        self.timings: Timings[TimingID]

    def initialize(self) -> None:
        """Set up the node maps, expectations, results and bunker models."""
        logger.info(
            "Initialize model before start of simulation", extra={"heading": True}
        )

        self._define_node_maps()
        self._initialize_expectations()
        self._initialize_results()
        self.timings = Timings(self.global_results.computational_time)
        self._initialize_bunker_models()

    def step(self, date: np.datetime64, inputs_changed: bool) -> None:
        """
        Perform the time step of the next date in the dateline.

        Parameters
        ----------
        date
            The date stepped to, its events already applied.
        inputs_changed
            Whether the date's events changed the deck's inputs.
        """
        with self.timings.step(self._idx, TimingID.OTHER):
            self._progress_date_time(date)
            self._perform_time_step(inputs_changed)

        self._idx += 1

    def finish(self) -> GlobalResults:
        """
        Post-process the completed time steps into the results of the run.

        Returns
        -------
        GlobalResults
            The model-wide results; each node holds its own.
        """
        self._post_process()

        return self.global_results

    def _progress_date_time(self, date: np.datetime64) -> None:
        self._time_step = timedelta_to_days(date - self._date)
        self._time += self._time_step
        self._date = date

        # the initial time step has no preceding date, so its size is taken as
        # one year
        if self._idx == 0:
            self._time_step = YEAR

    def _perform_time_step(self, inputs_changed: bool) -> None:
        self._check_dynamic_consistency()
        self._update_node_maps()

        # temporal calculators get the current time assigned or their value
        # precalculated, so they can be read through .get() without the time
        # being passed to every method
        self._pre_assign_temporal()
        self._calculate_expectations()

        self._update_vessel_operations()

        # only events change the deck's inputs, so the derived expectations are
        # recalculated at the first step and when a date's events change the inputs,
        # and otherwise hold the values written then
        if self._idx == 0 or inputs_changed:
            self._recalculate_derived_expectations()

        if self._idx == 0:
            self._initialize_existing_fleet()
            self._initialize_existing_production()

        # nothing the policy emission coefficients, vessel thresholds and levy costs
        # read (plant production and delivery WTT, port WTT overwrites, bunkering
        # flags and shore-power emission factors, the vessels' effective LHVs, the
        # levies' levels and the vessels each policy polices) changes later in the
        # step, so one pass serves both bunkering runs
        self._calculate_policy_emission_coefficients()

        # technology costs are excluded here: they enter the cargo charter
        # metrics below as the fleet-average carried technology charge
        self._calculate_asset_charter()

        if self._idx > 0:
            # ages advance before any calculation that depends on the existing
            # fleet or production capacity
            self._update_ages()

            # the fleet evolution expectations are updated before the expected
            # bunkering so that vessels allowed in the current time-step have a
            # non-zero multiplier
            self._update_fleet_evolution_expectation()

            self._calculate_potential_fuel_type_demand()
            self._calculate_fair_share_fuel_supply(BunkerScopeID.EXPECTED)

            # the times in port, electrical demands, shore-power capacities and cargo
            # miles are rewritten during the step, and the threshold adjustment of
            # each bunkering LP rewrites the regulation inputs of its own time step,
            # so the shore-power limits, the regulation measures and the regulation
            # bunkering inputs are recalculated before each bunkering run
            calculate_shore_power_limits(self.nodes.fleets, self._idx)
            self._calculate_regulation_measures()
            self._calculate_regulation_bunkering_inputs()

            # the bunker LP takes energy demands as given, so demands must fit
            # the installed converter power for it to be feasible
            self._verify_power_capacity(self._bunker_expected)
            self._calculate_expected_bunkering()

            # the fuel demand weights the expected bunkering with the expected
            # multipliers the LPs ran with, which the fleet evolution below rewrites
            self._calculate_fleet_fuel_demand()

            # smooth the energy-conservation LP duals into scarcity belief paths
            # consumed by the technology and speed-management heuristics below
            self._update_scarcity_signals()

            self._perform_fleet_technology_installation()
            self._perform_fleet_speed_management()

            # the freight costs determine the uptake of the vessel types in the
            # fleet evolution
            self._calculate_cargo_charter()
            self._perform_fleet_evolution()
            self._perform_producer_evolution()

        self._missing_technology_approximation()
        self._calculate_fuel_import()
        self._calculate_potential_fuel_type_demand()
        self._calculate_fair_share_fuel_supply(BunkerScopeID.EXISTING)

        calculate_shore_power_limits(self.nodes.fleets, self._idx)
        self._calculate_regulation_measures()
        self._calculate_regulation_bunkering_inputs()

        # re-verify against the installed converter power: the energy demands
        # have been rewritten since the expected bunkering pass
        self._verify_power_capacity(self._bunker_existing)
        self._perform_existing_bunkering()
        self._calculate_regulation_compliance(self._bunker_existing)
        self._calculate_individual_remedial_expenses(self._bunker_existing)
        self._calculate_flexibility_markets(self._bunker_existing)

        # the fuel-type balance weighs this step's existing bunkering; the results
        # below transfers the capacity just calculated, and the next step's fuel
        # conversion reads both totals
        self._calculate_fuel_type_balance()
        self._record_results()

    def _check_dynamic_consistency(self) -> None:
        """Raise where a node's time-varying attributes contradict each other."""
        times = self.timeline[self._idx :]
        dates = self.dateline[self._idx :]
        for node in self.nodes.all_nodes():
            node.check_dynamic_consistency(times, dates)

    def _pre_assign_temporal(self) -> None:
        """Precalculate forecasts and assign time to timetables."""
        for forecast in self.nodes.forecasts.values():
            forecast.precalculate(self._time)

        for timetable in self.nodes.timetables.values():
            timetable.set_current_time(self._time)

    def _update_node_maps(self) -> None:
        """Rewrite the node maps that events can change."""
        update_imposed_levies(self.nodes.ports, self.nodes.levies)

    def _calculate_expectations(self) -> None:
        """Calculate the per-step expectations later phases and other domains read."""
        emissions_lifetime = self.general_nodes.model_definition.emissions_lifetime

        calculate_policy_expectations(
            self.nodes.regulations,
            self.nodes.levies,
            self.nodes.emissions,
            self.nodes.routes,
            self.nodes.vessels,
            emissions_lifetime,
            self.timeline,
            self._idx,
        )

        calculate_fleet_expectations(self.nodes.vessels, self.nodes.emissions)

        calculate_port_expectations(self.nodes.ports, self.timeline, self._idx)
        calculate_export_expectations(self.nodes.producers, self.timeline, self._idx)

    def _update_vessel_operations(self) -> None:
        for fleet in self.nodes.fleets.values():
            allow_speed_management = fleet.allow_speed_management

            for vessel in fleet.vessels:
                update_operations(vessel, allow_speed_management, self._idx)

    def _recalculate_derived_expectations(self) -> None:
        """
        Recalculate the expectations derived from the deck's inputs alone.

        They are written from this step to the end of the horizon. A calculation
        belongs here only if it reads no simulation state and evaluates every
        calculator at an explicit time.
        """
        # the logistics read the lead times and lifetimes the production writes
        self._calculate_fuel_production_properties()
        self._calculate_fuel_logistics_properties()

    @timed(TimingID.PLANT_PRODUCTION)
    def _calculate_fuel_production_properties(self) -> None:
        for plant in self.nodes.plants.values():
            # the feed masses are summed over the plant's process tree into every
            # step from this one on, so they are cleared before each recalculation
            plant.expectation.reset_additive_properties(self._idx)
            calculate_plant_production_expectations(
                plant, self.nodes.emissions, self.timeline, self._idx
            )

    def _calculate_fuel_logistics_properties(self) -> None:
        calculate_plant_logistics_expectations(
            self.nodes.plants,
            self.nodes.ports,
            self.nodes.emissions,
            self.timeline,
            self._idx,
        )

    def _calculate_fuel_import(self) -> None:
        calculate_fuel_import_to_ports(
            self.nodes.ports,
            self.nodes.producers,
            self.nodes.emissions,
            self.nodes.fuels,
            self.timeline,
            self._idx,
        )

    @timed(TimingID.POLICY)
    def _calculate_policy_emission_coefficients(self) -> None:
        calculate_policy_emission_coefficients(
            self.nodes.regulations,
            self.nodes.levies,
            self.nodes.vessels,
            self.nodes.plants,
            self.timeline,
            self._idx,
        )

    @timed(TimingID.POLICY)
    def _calculate_regulation_measures(self) -> None:
        calculate_regulation_measures(
            self.nodes.regulations, self.nodes.vessels, self.timeline, self._idx
        )

    @timed(TimingID.POLICY)
    def _calculate_regulation_bunkering_inputs(self) -> None:
        calculate_regulation_bunkering_inputs(
            self.nodes.regulations, self.nodes.vessels, self._idx
        )

    def _calculate_potential_fuel_type_demand(self) -> None:
        calculate_potential_fuel_type_demand(self.nodes.fleets, self._idx)

    def _calculate_fair_share_fuel_supply(self, scope: BunkerScopeID) -> None:
        fuels = {
            fuel_name: fuel
            for fuel_name, fuel in self.nodes.fuels.items()
            if not fuel.liquid_market
        }
        calculate_fair_share_fuel_supply(self.nodes.fleets, fuels, self._idx, scope)

    def _verify_power_capacity(self, bunker: BunkerAlgorithm) -> None:
        vessels = bunker.get_admitted_vessels(self._idx)
        verify_power_capacity(vessels, self._idx)

    @timed(TimingID.PRODUCER_EVOLUTION)
    def _perform_producer_evolution(self) -> None:
        """
        Progress each producer in time and plan its pipeline from its share of the gap.

        Each producer first decommissions its retired plants, takes delivery from its
        pipeline, and updates its feed gap and development potential. The fuel
        supply/demand gap is then shared out among the producers, and each plans new
        plants into its pipeline, updates its feed gap again and recalculates its
        evolution expectation.
        """
        fuels = {
            fuel_name: fuel
            for fuel_name, fuel in self.nodes.fuels.items()
            if not fuel.liquid_market
        }

        for producer in self.nodes.producers.values():
            perform_decommissioning(producer)
            perform_pipeline_delivery(producer)
            calculate_feed_availability(producer, self.timeline, self._idx)
            calculate_development_potential(producer, self._time_step, self._idx)

        demand = calculate_expected_fuel_demand(self.nodes.fleets, self._idx)
        supply = calculate_expected_fuel_supply(self.nodes.producers, self._idx)
        gap = calculate_expected_fuel_gap(fuels, supply, demand)
        calculate_fair_share_demand(self.nodes.producers, gap, self._idx)

        for producer in self.nodes.producers.values():
            perform_pipeline_planning(
                producer, self.timeline, self._time_step, self._idx
            )

            # the feed gap is updated again before the evolution expectation, to
            # account for the plants just added to the pipeline
            calculate_feed_availability(producer, self.timeline, self._idx)
            calculate_producer_evolution_expectation(producer, self.timeline, self._idx)

    def _update_ages(self) -> None:
        for fleet in self.nodes.fleets.values():
            update_vessel_ages(fleet, self._time_step)

        for producer in self.nodes.producers.values():
            update_plant_ages(producer, self._time_step)

    def _update_fleet_evolution_expectation(self) -> None:
        for fleet in self.nodes.fleets.values():
            calculate_fleet_evolution_expectation(fleet, self.timeline, self._idx)

    def _calculate_expected_bunkering(self) -> None:
        for vessel in self.nodes.vessels.values():
            vessel.expectation.reset_expected_bunkering()

        for regulation in self.nodes.regulations.values():
            regulation.expectation.reset_expected_bunkering()

        bunker = self._bunker_expected

        for i in range(self._idx, self.timeline.size):
            time_step_i = self.timeline[i] - self.timeline[i - 1]

            self._perform_bunkering(bunker, i, self.timeline[i], time_step_i)

            self._calculate_individual_remedial_expenses(bunker)
            self._calculate_flexibility_markets(bunker)

    def _calculate_fleet_fuel_demand(self) -> None:
        for fleet in self.nodes.fleets.values():
            calculate_fleet_fuel_demand(fleet, self.nodes.fuels, self._idx)

    def _update_scarcity_signals(self) -> None:
        update_vessel_scarcity_beliefs(self.nodes.fleets, self.timeline, self._idx)
        update_regulation_flexibility_beliefs(
            self.nodes.regulations, self.nodes.vessels, self.timeline, self._idx
        )
        record_investment_signals(self.nodes.fleets, self._idx)

    @timed(TimingID.SPEED_MANAGEMENT)
    def _perform_fleet_speed_management(self) -> None:
        for fleet in self.nodes.fleets.values():
            perform_speed_management(fleet, self._time_step, self._idx)

    @timed(TimingID.TECHNOLOGY_INSTALLATION)
    def _perform_fleet_technology_installation(self) -> None:
        for fleet in self.nodes.fleets.values():
            perform_technology_installation(
                fleet, self.timeline, self._time_step, self._idx
            )

    def _calculate_asset_charter(self) -> None:
        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                calculate_asset_charter(vessel, self.timeline, self._idx)

    def _calculate_cargo_charter(self) -> None:
        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                calculate_cargo_charter(vessel, self.timeline, self._idx)

    @timed(TimingID.FLEET_EVOLUTION)
    def _perform_fleet_evolution(self) -> None:
        """
        Evolve each fleet by one time-step and recalculate its evolution expectation.

        Each fleet scraps its oldest vessels, converts vessels to other fuels and
        closes the gap between its trade and the capacity left. The residual energy
        demand and technology uptake of the resulting fleet are then updated.
        """
        for fleet in self.nodes.fleets.values():
            perform_primary_scrapping(fleet, self._time_step, self._idx)
            perform_fuel_conversions(fleet, self.timeline, self._time_step, self._idx)
            close_trade_gap(fleet, self._time_step, self._idx)

            # the residual energy demand reads the updated fleet composition
            update_residual_energy_demand(fleet, self._idx)

            # refresh the fleet-average carried technology charge after evolution, so
            # it reflects this timestep's scrapping, conversions and newbuilds (the
            # pre-evolution transfer already served the cargo charter)
            transfer_technology_charter_rate(fleet, self._idx)

            calculate_fleet_evolution_expectation(fleet, self.timeline, self._idx)

    def _perform_existing_bunkering(self) -> None:
        bunker = self._bunker_existing
        self._perform_bunkering(bunker, self._idx, self._time, self._time_step)

    def _perform_bunkering(
        self, bunker: BunkerAlgorithm, idx: int, time: float, time_step: float
    ) -> None:
        """
        Build, solve and transfer the bunkering LP of one evaluated time step.

        The LP is solved again where the threshold adjustment rewrote its regulation
        inputs after the first solve.
        """
        bunker.build(self._idx, idx, time, time_step)
        bunker.solve()
        bunker.transfer_regulation_solution()

        if self._calculate_adjusted_regulation_thresholds(bunker):
            bunker.update_regulation_constraints()
            bunker.solve()

        bunker.transfer()

    @timed(TimingID.POLICY)
    def _calculate_adjusted_regulation_thresholds(
        self, bunker: BunkerAlgorithm
    ) -> bool:
        return calculate_adjusted_regulation_thresholds(
            self.nodes.regulations, self.nodes.vessels, bunker.multipliers, bunker.idx
        )

    @timed(TimingID.POLICY)
    def _calculate_regulation_compliance(self, bunker: BunkerAlgorithm) -> None:
        calculate_regulation_compliance(
            self.nodes.regulations, bunker.multipliers, bunker.idx
        )

    @timed(TimingID.POLICY)
    def _calculate_individual_remedial_expenses(self, bunker: BunkerAlgorithm) -> None:
        calculate_individual_remedial_expenses(
            self.nodes.regulations,
            self.nodes.vessels,
            bunker.multipliers,
            bunker.scope,
            bunker.idx,
        )

    @timed(TimingID.POLICY)
    def _calculate_flexibility_markets(self, bunker: BunkerAlgorithm) -> None:
        calculate_flexibility_markets(
            self.nodes.regulations,
            self.nodes.vessels,
            bunker.multipliers,
            bunker.scope,
            bunker.idx,
        )

    def _missing_technology_approximation(self) -> None:
        """
        Estimate energy-efficiency uptake for fleets that cannot retrofit.

        The estimate uses the fleet-average savings of the fleets that have them.
        """
        approximate_missing_technology(self.nodes.fleets, self._idx)

    def _define_node_maps(self) -> None:
        """Write the node maps derived from DSL-defined attributes."""
        define_vessel_fuel_maps(self.nodes.vessels, self.nodes.fuels)

    def _initialize_bunker_models(self) -> None:
        # the solver backend is chosen before any model is created
        set_solver_preference(self.general_nodes.bunker_options.solver)

        self._bunker_existing.initialize(
            self.nodes.emissions,
            self.nodes.feedstocks,
            self.nodes.fleets,
            self.nodes.fuels,
            self.nodes.ports,
            self.nodes.regulations,
            self.general_nodes.bunker_options,
            BunkerScopeID.EXISTING,
            output_directory=self._output_directory,
            timings=self.timings,
        )
        self._bunker_expected.initialize(
            self.nodes.emissions,
            self.nodes.feedstocks,
            self.nodes.fleets,
            self.nodes.fuels,
            self.nodes.ports,
            self.nodes.regulations,
            self.general_nodes.bunker_options,
            BunkerScopeID.EXPECTED,
            output_directory=self._output_directory,
            timings=self.timings,
        )

    def _initialize_expectations(self) -> None:
        length = self.timeline.size

        for fleet in self.nodes.fleets.values():
            fleet.initialize_expectation(length, self.nodes.fuels)

        for levy in self.nodes.levies.values():
            levy.initialize_expectation(length)

        for plant in self.nodes.plants.values():
            plant.initialize_expectation(
                length,
                self.nodes.emissions,
                self.nodes.feedstocks,
                self.nodes.ports,
                self.nodes.processes,
            )

        for port in self.nodes.ports.values():
            port.initialize_expectation(length, self.nodes.fuels, self.nodes.emissions)

        for producer in self.nodes.producers.values():
            producer.initialize_expectation(
                length,
                self.nodes.feedstocks,
                self.nodes.fuels,
                self.nodes.ports,
                self.nodes.processes,
            )

        for regulation in self.nodes.regulations.values():
            regulation.initialize_expectation(
                length, self.nodes.routes, self.nodes.vessels
            )

        for vessel in self.nodes.vessels.values():
            vessel.initialize_expectation(
                length, self.nodes.fuels, self.nodes.emissions
            )

    def _initialize_results(self) -> None:
        context = ResultsContext.from_nodes(
            self.timeline / YEAR,
            self.nodes.fuels,
            self.nodes.emissions,
            self.general_nodes.model_definition.emissions_lifetime,
        )

        regulation_names = list(self.nodes.regulations.keys())
        levy_names = list(self.nodes.levies.keys())

        self.global_results.initialize(
            context,
            self.nodes.feedstocks,
            self.nodes.processes,
            regulation_names,
            levy_names,
        )

        for fleet in self.nodes.fleets.values():
            fleet.initialize_results(context, regulation_names, levy_names)

        for levy in self.nodes.levies.values():
            levy.initialize_results(context)

        for plant in self.nodes.plants.values():
            plant.initialize_results(context)

        for port in self.nodes.ports.values():
            port.initialize_results(context)

        for producer in self.nodes.producers.values():
            producer.initialize_results(
                context, self.nodes.feedstocks, self.nodes.processes
            )

        for regulation in self.nodes.regulations.values():
            regulation.initialize_results(context, self.nodes.vessels)

        for vessel in self.nodes.vessels.values():
            vessel.initialize_results(context, regulation_names, levy_names)

    def _initialize_existing_fleet(self) -> None:
        for vessel in self.nodes.vessels.values():
            determine_fuel_type(vessel)
            check_fuel_options(vessel)

        assign_vessels_to_fleets(self.nodes.fleets.values())

        for fleet in self.nodes.fleets.values():
            initialize_existing_fleet(fleet, self.timeline)

    def _initialize_existing_production(self) -> None:
        for producer in self.nodes.producers.values():
            initialize_existing_producer(producer, self.timeline)

    def _calculate_fuel_type_balance(self) -> None:
        for fleet in self.nodes.fleets.values():
            calculate_fuel_type_balance(fleet, self.nodes.fuels, self._idx)

    def _record_results(self) -> None:
        for fleet in self.nodes.fleets.values():
            record_fleet_results(fleet, self.timeline, self._idx)

        for plant in self.nodes.plants.values():
            record_plant_results(plant, self._idx)

        for port in self.nodes.ports.values():
            record_port_results(port, self._idx)

        for producer in self.nodes.producers.values():
            record_producer_results(producer, self.timeline, self._idx)

        for regulation in self.nodes.regulations.values():
            record_regulation_results(regulation, self._idx)

        for vessel in self.nodes.vessels.values():
            record_vessel_results(vessel, self._idx)

    def _post_process(self) -> None:
        logger.info(
            "Post-process model after end of simulation", extra={"heading": True}
        )

        # every vessel before any fleet: a fleet's achieved rates read its vessels'
        # completed expenses, and a vessel may be kept without a fleet
        for vessel in self.nodes.vessels.values():
            complete_vessel_results(vessel)

        for fleet in self.nodes.fleets.values():
            complete_fleet_results(fleet, self.timeline)
            self.global_results.add_fuel_consumer_results(fleet.results)
            self.global_results.add_vessel_aggregate_results(fleet.results)

        for port in self.nodes.ports.values():
            complete_port_results(port.results)
            self.global_results.add_fuel_infrastructure_results(port.results)

        for producer in self.nodes.producers.values():
            complete_producer_results(producer.results)
            self.global_results.add_fuel_producer_results(producer.results)
            self.global_results.add_plant_aggregate_results(producer.results)

        complete_global_fleet_results(self.global_results)
        complete_global_fuel_results(self.global_results)

        for plant in self.nodes.plants.values():
            complete_plant_results(plant.results)

        for regulation in self.nodes.regulations.values():
            complete_regulation_results(regulation.results)
