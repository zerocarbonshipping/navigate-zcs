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

from navigate.core import (
    define_vessel_fuel_maps,
    define_vessels_in_jurisdiction,
    update_bunkerable_fuels,
    update_imposed_levies,
)
from navigate.core.enum_ import BunkerScopeID, TimingID
from navigate.core.results import GlobalResults, ResultsContext
from navigate.exceptions import DeckError
from navigate.simulation.bunker import (
    BunkerAlgorithm,
    calculate_fair_share_fuel_supply,
    select_backend,
)
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
from navigate.util import YEAR, Timings, dates_to_days, timed

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.enum_ import SolverBackendID
    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.core.nodes.fuel import Fuel
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
    registries = {"Fleets": nodes.fleets, "Fuels": nodes.fuels}
    missing = [label for label, registry in registries.items() if not registry]
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
    infeasible_lp_file
        File the bunkering LP writes an infeasible model to, its IIS beside it.
    """

    def __init__(
        self,
        nodes: Nodes,
        general_nodes: GeneralNodes,
        dateline: DateArray,
        infeasible_lp_file: Path,
    ) -> None:
        check_runnable(nodes)

        self.nodes: Nodes = nodes
        self.general_nodes: GeneralNodes = general_nodes
        self._infeasible_lp_file: Path = infeasible_lp_file

        # the simulation's dates, and the elapsed time in days since the start date
        self.dateline: DateArray = dateline
        self.timeline: FloatArray = dates_to_days(self.dateline)

        # the index of the current time step, and its size in days
        self._idx: int = 0
        self._time_step: float

        self.global_results: GlobalResults = GlobalResults()
        self.timings: Timings[TimingID]

        self._bunker_existing: BunkerAlgorithm
        self._bunker_expected: BunkerAlgorithm

        self._produced_fuels: dict[str, Fuel] = {}

        for name, fuel in nodes.fuels.items():
            if not fuel.liquid_market:
                self._produced_fuels[name] = fuel

    def initialize(self) -> None:
        """Set up the node maps, expectations, results and bunker models."""
        logger.info(
            "Initialize model before start of simulation", extra={"heading": True}
        )

        self._define_node_maps()
        self._initialize_expectations()
        self._initialize_results()
        self.timings = Timings(self.global_results.computational_time)
        self._initialize_bunkers()

    def step(self, inputs_changed: bool) -> None:
        """
        Perform the time step of the next date in the dateline, its events applied.

        Parameters
        ----------
        inputs_changed
            Whether the date's events changed the deck's inputs.
        """
        with self.timings.step(self._idx, TimingID.OTHER):
            self._time_step = self._time_step_at(self._idx)
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
        logger.info(
            "Post-process model after end of simulation", extra={"heading": True}
        )

        # every vessel before any fleet: a fleet's achieved rates read its vessels'
        # completed expenses, and a vessel may be kept without a fleet
        for vessel in self.nodes.vessels.values():
            complete_vessel_results(vessel)

        for fleet in self.nodes.fleets.values():
            complete_fleet_results(fleet, self.timeline)
            self.global_results.add_vessel_aggregate_results(fleet.results)

        for port in self.nodes.ports.values():
            complete_port_results(port.results)
            self.global_results.add_fuel_infrastructure_results(port.results)

        for producer in self.nodes.producers.values():
            complete_producer_results(producer.results)
            self.global_results.add_plant_aggregate_results(producer.results)

        complete_global_fleet_results(self.global_results)
        complete_global_fuel_results(self.global_results)

        for plant in self.nodes.plants.values():
            complete_plant_results(plant.results)

        for regulation in self.nodes.regulations.values():
            complete_regulation_results(regulation.results)

        return self.global_results

    def _define_node_maps(self) -> None:
        """Write the node maps derived from DSL-defined attributes."""
        define_vessel_fuel_maps(self.nodes.vessels, self.nodes.fuels)
        define_vessels_in_jurisdiction(self.nodes.levies, self.nodes.vessels)
        define_vessels_in_jurisdiction(self.nodes.regulations, self.nodes.vessels)

    def _initialize_expectations(self) -> None:
        nodes = self.nodes
        length = self.timeline.size

        for fleet in nodes.fleets.values():
            fleet.initialize_expectation(length, nodes.fuels)

        for levy in nodes.levies.values():
            levy.initialize_expectation(length)

        for plant in nodes.plants.values():
            plant.initialize_expectation(
                length, nodes.emissions, nodes.feedstocks, nodes.ports, nodes.processes
            )

        for port in nodes.ports.values():
            port.initialize_expectation(length, nodes.fuels, nodes.emissions)

        for producer in nodes.producers.values():
            producer.initialize_expectation(
                length, nodes.feedstocks, nodes.fuels, nodes.ports, nodes.processes
            )

        for regulation in nodes.regulations.values():
            regulation.initialize_expectation(length, nodes.routes, nodes.vessels)

        for vessel in nodes.vessels.values():
            vessel.initialize_expectation(length, nodes.fuels, nodes.emissions)

    def _initialize_results(self) -> None:
        nodes = self.nodes

        context = ResultsContext.from_nodes(
            self.timeline / YEAR,
            nodes.fuels,
            nodes.emissions,
            self.general_nodes.model_definition.emissions_lifetime,
        )

        feedstock_names = list(nodes.feedstocks.keys())
        levy_names = list(nodes.levies.keys())
        process_names = list(nodes.processes.keys())
        regulation_names = list(nodes.regulations.keys())
        vessel_names = list(nodes.vessels.keys())

        self.global_results.initialize(
            context, feedstock_names, process_names, regulation_names, levy_names
        )

        for fleet in nodes.fleets.values():
            fleet.initialize_results(context, regulation_names, levy_names)

        for levy in nodes.levies.values():
            levy.initialize_results(context)

        for plant in nodes.plants.values():
            plant.initialize_results(context)

        for port in nodes.ports.values():
            port.initialize_results(context)

        for producer in nodes.producers.values():
            producer.initialize_results(context, feedstock_names, process_names)

        for regulation in nodes.regulations.values():
            regulation.initialize_results(context, vessel_names)

        for vessel in nodes.vessels.values():
            vessel.initialize_results(context, regulation_names, levy_names)

    def _initialize_bunkers(self) -> None:
        backend = select_backend(self.general_nodes.bunker_options.solver)

        self._bunker_existing = self._create_bunker(BunkerScopeID.EXISTING, backend)
        self._bunker_expected = self._create_bunker(BunkerScopeID.EXPECTED, backend)

    def _create_bunker(
        self, scope: BunkerScopeID, backend: SolverBackendID
    ) -> BunkerAlgorithm:
        return BunkerAlgorithm(
            self.nodes.emissions,
            self.nodes.fleets,
            self.nodes.fuels,
            self.nodes.ports,
            self.nodes.regulations,
            self.general_nodes.bunker_options,
            backend,
            scope,
            infeasible_lp_file=self._infeasible_lp_file,
            timings=self.timings,
        )

    def _time_step_at(self, idx: int) -> float:
        """Return the size of the time step ending at a date, in days."""
        # the first time step has no preceding date, so its size is taken as one year
        if idx == 0:
            return YEAR

        time_step: float = self.timeline[idx] - self.timeline[idx - 1]
        return time_step

    def _perform_time_step(self, inputs_changed: bool) -> None:
        is_first_step = self._idx == 0

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
        if is_first_step or inputs_changed:
            self._recalculate_derived_expectations()

        if is_first_step:
            self._initialize_existing_fleet()
            self._initialize_existing_production()

        # nothing the policy emission coefficients, vessel thresholds and levy costs
        # read (plant production and delivery WTT, port WTT overwrites, bunkering
        # flags and shore-power emission factors, the vessels' effective LHVs, the
        # levies' levels and the vessels each policy polices) changes later in the
        # step, so one pass serves both bunkering runs
        self._calculate_policy_emission_coefficients()

        self._calculate_asset_charter()

        if not is_first_step:
            self._perform_evolution()

        self._approximate_missing_technology()
        self._calculate_fuel_import()

        self._prepare_bunkering(self._bunker_existing)
        self._perform_existing_bunkering()

        # the fuel-type balance weighs this step's existing bunkering; the results
        # recorded below transfer the capacity just calculated, and the next step's
        # fuel conversion reads both totals
        self._calculate_fuel_type_balance()
        self._record_results()

    def _check_dynamic_consistency(self) -> None:
        """Raise where a node's time-varying attributes contradict each other."""
        times = self.timeline[self._idx :]
        dates = self.dateline[self._idx :]
        for node in self.nodes.all_nodes():
            node.check_dynamic_consistency(times, dates)

    def _update_node_maps(self) -> None:
        """Rewrite the node maps that events can change."""
        update_bunkerable_fuels(self.nodes.vessels)
        update_imposed_levies(self.nodes.ports, self.nodes.levies)

    def _pre_assign_temporal(self) -> None:
        """Precalculate forecasts and assign time to timetables."""
        time = self.timeline[self._idx]

        for forecast in self.nodes.forecasts.values():
            forecast.precalculate(time)

        for timetable in self.nodes.timetables.values():
            timetable.set_current_time(time)

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
            for vessel in fleet.vessels:
                update_operations(vessel, fleet.allow_speed_management, self._idx)

    def _recalculate_derived_expectations(self) -> None:
        """
        Recalculate the expectations derived from the deck's inputs alone.

        They are written from this step to the end of the horizon. A calculation
        belongs here only if it reads no simulation state and evaluates every
        calculator at an explicit time.
        """
        # the logistics read the lead times and lifetimes the production writes
        self._calculate_plant_production_expectations()
        self._calculate_plant_logistics_expectations()

    @timed(TimingID.PLANT_PRODUCTION)
    def _calculate_plant_production_expectations(self) -> None:
        """
        Calculate each plant's production expectations from this step on.

        The feed masses are summed over the plant's process tree into every step from
        this one on, so they are cleared before each recalculation.
        """
        for plant in self.nodes.plants.values():
            plant.expectation.reset_feed_conversion(self._idx)
            calculate_plant_production_expectations(
                plant, self.nodes.emissions, self.timeline, self._idx
            )

    def _calculate_plant_logistics_expectations(self) -> None:
        calculate_plant_logistics_expectations(
            self.nodes.plants,
            self.nodes.ports,
            self.nodes.emissions,
            self.timeline,
            self._idx,
        )

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

    def _calculate_asset_charter(self) -> None:
        """
        Calculate the asset charter of every fleet's vessels.

        Technology costs are excluded: they enter the cargo charter metrics as the
        fleet-average carried technology charge.
        """
        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                calculate_asset_charter(vessel, self.timeline, self._idx)

    def _perform_evolution(self) -> None:
        """
        Evolve the fleets and producers by one time step on the expected bunkering.

        The expected bunkering runs from this step to the end of the horizon first;
        the fleets' technology, speeds and composition and the producers' pipelines
        then evolve on the fuel demand and scarcity it foresees.
        """
        # ages advance before any calculation that depends on the existing
        # fleet or production capacity
        self._update_ages()

        # the fleet evolution expectations are calculated before the expected
        # bunkering so that vessels allowed in the current time step have a
        # non-zero multiplier
        self._calculate_fleet_evolution_expectations()

        self._prepare_bunkering(self._bunker_expected)
        self._perform_expected_bunkering()

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

    def _update_ages(self) -> None:
        for fleet in self.nodes.fleets.values():
            update_vessel_ages(fleet, self._time_step)

        for producer in self.nodes.producers.values():
            update_plant_ages(producer, self._time_step)

    def _calculate_fleet_evolution_expectations(self) -> None:
        for fleet in self.nodes.fleets.values():
            calculate_fleet_evolution_expectation(fleet, self.timeline, self._idx)

    def _prepare_bunkering(self, bunker: BunkerAlgorithm) -> None:
        """
        Calculate the inputs of a bunkering run and verify the vessels it admits.

        The times in port, electrical demands, shore-power capacities and cargo miles
        are rewritten during the step, and the threshold adjustment of each bunkering
        LP rewrites the regulation inputs of its own time step, so these inputs are
        recalculated before each run. The LP takes energy demands as given, so the
        demands must fit the installed converter power for it to be feasible.
        """
        self._calculate_potential_fuel_type_demand()
        self._calculate_fair_share_fuel_supply(bunker.scope)
        self._calculate_shore_power_limits()
        self._calculate_regulation_measures()
        self._calculate_regulation_bunkering_inputs()

        self._verify_power_capacity(bunker)

    def _calculate_potential_fuel_type_demand(self) -> None:
        calculate_potential_fuel_type_demand(self.nodes.fleets, self._idx)

    def _calculate_fair_share_fuel_supply(self, scope: BunkerScopeID) -> None:
        calculate_fair_share_fuel_supply(
            self.nodes.fleets, self._produced_fuels, self._idx, scope
        )

    def _calculate_shore_power_limits(self) -> None:
        calculate_shore_power_limits(self.nodes.fleets, self._idx)

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

    def _verify_power_capacity(self, bunker: BunkerAlgorithm) -> None:
        vessels = bunker.get_admitted_vessels(self._idx)
        verify_power_capacity(vessels, self._idx)

    def _perform_expected_bunkering(self) -> None:
        """Run the expected bunkering of every step from this one to the horizon."""
        bunker = self._bunker_expected

        for vessel in self.nodes.vessels.values():
            vessel.expectation.reset_expected_bunkering()

        for regulation in self.nodes.regulations.values():
            regulation.expectation.reset_expected_bunkering()

        for i in range(self._idx, self.timeline.size):
            self._perform_bunkering(bunker, i)

            self._calculate_individual_remedial_expenses(bunker)
            self._calculate_flexibility_markets(bunker)

    def _perform_bunkering(self, bunker: BunkerAlgorithm, idx: int) -> None:
        """
        Build, solve and transfer the bunkering LP of one evaluated time step.

        The LP is solved again where the threshold adjustment rewrote its regulation
        inputs after the first solve.
        """
        time = self.timeline[idx]
        time_step = self._time_step_at(idx)

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

    def _calculate_fleet_fuel_demand(self) -> None:
        for fleet in self.nodes.fleets.values():
            calculate_fleet_fuel_demand(fleet, self.nodes.fuels, self._idx)

    def _update_scarcity_signals(self) -> None:
        update_vessel_scarcity_beliefs(self.nodes.fleets, self.timeline, self._idx)
        update_regulation_flexibility_beliefs(
            self.nodes.regulations, self.nodes.vessels, self.timeline, self._idx
        )
        record_investment_signals(self.nodes.fleets, self._idx)

    @timed(TimingID.TECHNOLOGY_INSTALLATION)
    def _perform_fleet_technology_installation(self) -> None:
        for fleet in self.nodes.fleets.values():
            perform_technology_installation(
                fleet, self.timeline, self._time_step, self._idx
            )

    @timed(TimingID.SPEED_MANAGEMENT)
    def _perform_fleet_speed_management(self) -> None:
        for fleet in self.nodes.fleets.values():
            perform_speed_management(fleet, self._time_step, self._idx)

    def _calculate_cargo_charter(self) -> None:
        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                calculate_cargo_charter(vessel, self.timeline, self._idx)

    @timed(TimingID.FLEET_EVOLUTION)
    def _perform_fleet_evolution(self) -> None:
        """
        Evolve each fleet by one time step and recalculate its evolution expectation.

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
            # it reflects this time step's scrapping, conversions and newbuilds (the
            # pre-evolution transfer already served the cargo charter)
            transfer_technology_charter_rate(fleet, self._idx)

            calculate_fleet_evolution_expectation(fleet, self.timeline, self._idx)

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
        for producer in self.nodes.producers.values():
            perform_decommissioning(producer)
            perform_pipeline_delivery(producer)
            calculate_feed_availability(producer, self.timeline, self._idx)
            calculate_development_potential(producer, self._time_step, self._idx)

        demand = calculate_expected_fuel_demand(self.nodes.fleets, self._idx)
        supply = calculate_expected_fuel_supply(self.nodes.producers, self._idx)
        gap = calculate_expected_fuel_gap(self._produced_fuels, supply, demand)
        calculate_fair_share_demand(self.nodes.producers, gap, self._idx)

        for producer in self.nodes.producers.values():
            perform_pipeline_planning(
                producer, self.timeline, self._time_step, self._idx
            )

            # the feed gap is updated again before the evolution expectation, to
            # account for the plants just added to the pipeline
            calculate_feed_availability(producer, self.timeline, self._idx)
            calculate_producer_evolution_expectation(producer, self.timeline, self._idx)

    def _approximate_missing_technology(self) -> None:
        """
        Estimate energy-efficiency uptake for fleets that cannot retrofit.

        The estimate uses the fleet-average savings of the fleets that have them.
        """
        approximate_missing_technology(self.nodes.fleets, self._idx)

    def _calculate_fuel_import(self) -> None:
        calculate_fuel_import_to_ports(
            self.nodes.ports,
            self.nodes.producers,
            self.nodes.emissions,
            self.nodes.fuels,
            self.timeline,
            self._idx,
        )

    def _perform_existing_bunkering(self) -> None:
        """Run the existing bunkering of this step and settle its regulations."""
        bunker = self._bunker_existing

        self._perform_bunkering(bunker, self._idx)

        self._calculate_regulation_compliance(bunker)
        self._calculate_individual_remedial_expenses(bunker)
        self._calculate_flexibility_markets(bunker)

    @timed(TimingID.POLICY)
    def _calculate_regulation_compliance(self, bunker: BunkerAlgorithm) -> None:
        calculate_regulation_compliance(
            self.nodes.regulations, bunker.multipliers, bunker.idx
        )

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
