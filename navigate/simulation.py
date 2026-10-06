# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The simulation loop: SimulationManager runs a deck from its nodes to its output.

The CLI constructs and runs it; a finished run hands its SimulationResults to the
reports and figures in navigate.output.
"""

from __future__ import annotations

import logging
import math
import timeit
from typing import TYPE_CHECKING

import numpy as np

from navigate.bunker import BunkerAlgorithm, calculate_fair_share_fuel_supply
from navigate.bunker.solver import set_solver_preference
from navigate.core import SimulationResults, get_fuels_per_fuel_type
from navigate.core.enum_ import BunkerScopeID
from navigate.core.profiles import ManagerProfile
from navigate.fleet import (
    approximate_missing_technology,
    assign_vessels_to_fleets,
    calculate_cargo_charter_properties,
    calculate_evolution_expectation,
    calculate_fleet_profile,
    calculate_vessel_charter_properties,
    determine_fuel_type,
    determine_usable_fuel_types,
    determine_usable_fuels,
    initialize_existing_fleet,
    perform_fleet_evolution,
    perform_speed_management,
    perform_technology_installation,
    post_process_fleet_profile,
    post_process_investment_metric,
    record_investment_signals,
    update_operational_profile,
    update_vessel_scarcity_beliefs,
    verify_power_capacity,
)
from navigate.fuel import (
    calculate_constrained_fair_share_fuel_demand,
    calculate_development_potential,
    calculate_expected_fuel_demand,
    calculate_expected_fuel_supply,
    calculate_export_expectation,
    calculate_fuel_import_to_ports,
    calculate_fuel_supply_demand_gap,
    calculate_plant_logistics_expectations,
    calculate_plant_production_expectations,
    calculate_producer_profile,
    initialize_existing_producer,
    perform_planning,
    perform_progression,
)
from navigate.logging_ import (
    log_model_post_process,
    log_start_of_simulation,
    log_time_step_breaker,
)
from navigate.output import write_report
from navigate.parser import Parser
from navigate.policy import (
    calculate_policy_emission_coefficients,
    update_regulation_flexibility_beliefs,
)
from navigate.util import YEAR, dates_to_days, timedelta_to_days

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.core.enum_ import SolverBackendID
    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.util.types_ import DateArray, FloatArray

logger = logging.getLogger(__name__)


class SimulationManager:
    """
    Run a simulation deck, from the read deck to the exported results.

    Parameters
    ----------
    path
        Path to the simulation deck.
    data_dir
        Assumptions data folder.
    solver
        Solver backend that overrides the deck's BunkerOptions setting, or None
        to keep the deck's setting.
    """

    def __init__(
        self,
        path: Path,
        data_dir: Path | None = None,
        solver: SolverBackendID | None = None,
    ) -> None:
        # resolved as the parser resolves it, so the deck location matches the deck read
        deck_path = path.resolve()

        # parser -----------------------------------------------------------------------
        self.parser: Parser = Parser()
        self.nodes: Nodes = self.parser.nodes
        self.parser.read_deck(deck_path, data_dir=data_dir)
        self.general_nodes: GeneralNodes = self.parser.general_nodes

        if solver is not None:
            self.general_nodes.bunker_options.solver = solver

        # deck location, where the output is written
        self.deck_directory: str = str(deck_path.parent)
        self.deck_name: str = deck_path.stem

        # properties -------------------------------------------------------------------
        # the current time-step size and elapsed simulation time, in days
        self._time_step: float = 0.0
        self._time: float = 0.0
        self._date: np.datetime64 = self.general_nodes.model_definition.start_date
        self._idx: int = 0

        # the simulation's dates, and the elapsed time in days since the start date
        self.dateline: DateArray = self.parser.dates
        self.timeline: FloatArray = dates_to_days(self.dateline)

        # profile
        self.profile: ManagerProfile = ManagerProfile()

        # bunker algorithm -------------------------------------------------------------
        self._bunker_existing: BunkerAlgorithm = BunkerAlgorithm()
        self._bunker_expected: BunkerAlgorithm = BunkerAlgorithm()

        # results ----------------------------------------------------------------------
        self.results: SimulationResults

        # code timing ------------------------------------------------------------------
        self._computational_time: float

    def run(self) -> None:
        """Run the simulation as defined in the deck, handling its high-level flow."""
        self.parser.includes_necessary_information()
        self._computational_time = timeit.default_timer()

        self._initialize_simulation()
        self._run_simulation()

        self._post_process()
        self.results = SimulationResults(
            dateline=self.dateline,
            profile=self.profile,
            nodes=self.nodes,
            general_nodes=self.general_nodes,
        )
        self._export_reports()

        print(f"Finished simulation, {self.get_elapsed_time()}.")

    def _initialize_simulation(self) -> None:
        """Set up the expectations, profiles and bunker models the time steps use."""
        log_start_of_simulation(logger, self._date)

        self._initialize_expectations()
        self._initialize_profiles()
        self._initialize_bunker_models()

    def _run_simulation(self) -> None:
        """
        Step through the dateline, from the initial conditions at 'Start' on.

        Each date logs its time-step banner, applies its events, then steps.
        """
        for date in self.dateline:
            if self._idx > 0:
                log_time_step_breaker(
                    logger, self._idx, date, timedelta_to_days(date - self.dateline[0])
                )
            self.parser.read_events(date)
            self._progress_date_time(date)
            self._perform_time_step()
            self._idx += 1

    def _progress_date_time(self, date: np.datetime64) -> None:
        self._time_step = timedelta_to_days(date - self._date)
        self._time += self._time_step
        self._date = date

        # the initial time step has no preceding date, so its size is taken as
        # one year
        if self._idx == 0:
            self._time_step = YEAR

    def _perform_time_step(self) -> None:
        print(f"Date: {self._date}")

        self._check_dynamic_consistency()

        # temporal calculators get the current time assigned or their value
        # precalculated, so they can be read through .get() without the time
        # being passed to every method
        start_time = timeit.default_timer()
        self._pre_assign_temporal()
        self._calculate_expectations()
        self.profile.add_temporal_time(timeit.default_timer() - start_time, self._idx)

        self._calculate_vessel_operational_profile()
        self._calculate_fuel_production_properties()
        self._calculate_fuel_logistics_properties()

        if self._idx == 0:
            start_time_overhead = timeit.default_timer()
            self._initialize_existing_fleet()
            self._initialize_existing_production()
            self.profile.add_overhead_time(
                timeit.default_timer() - start_time_overhead, self._idx
            )

        # nothing the policy coefficients read (plant production and delivery WTT,
        # port WTT overwrites and bunkering flags, the vessels' usable fuels and
        # converters) changes later in the step, so one pass serves both
        # bunkering runs
        self._calculate_policy_emission_coefficients()

        # technology costs are excluded here: they enter the cargo charter
        # metrics below as the fleet-average carried technology charge
        self._calculate_vessel_charter_properties()

        if self._idx > 0:
            # ages advance before any calculation that depends on the existing
            # fleet or production capacity
            self._update_increment_ages()

            # the fleet evolution expectations are updated before the expected
            # bunkering so that vessels allowed in the current time-step have a
            # non-zero multiplier
            self._update_fleet_evolution_expectation()

            self._calculate_fair_share_fuel_supply(BunkerScopeID.EXPECTED)

            # the bunker LP takes energy demands as given, so demands must fit
            # the installed converter power for it to be feasible
            self._verify_power_capacity(BunkerScopeID.EXPECTED)
            self._calculate_expected_bunkering()

            # smooth the energy-conservation LP duals into scarcity belief paths
            # consumed by the technology and speed-management heuristics below
            self._update_scarcity_signals()

            self._perform_fleet_technology_installation()
            self._perform_fleet_speed_management()

            # the freight costs determine the uptake of the vessel types in the
            # fleet evolution
            self._calculate_cargo_charter_properties()
            self._perform_fleet_evolution()
            self._perform_producer_evolution()

        self._missing_technology_approximation()
        self._calculate_fuel_import()
        self._calculate_fair_share_fuel_supply(BunkerScopeID.EXISTING)

        # re-verify against the installed converter power: the energy demands
        # have been rewritten since the expected bunkering pass
        self._verify_power_capacity(BunkerScopeID.EXISTING)
        self._perform_existing_bunkering()

        self._calculate_profile()
        self.profile.set_total_time(
            self._idx, timeit.default_timer() - self._computational_time
        )

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

    def _calculate_expectations(self) -> None:
        """Precalculate certain expectations which are simulation bottlenecks."""
        emissions_lifetime = self.general_nodes.model_definition.emissions_lifetime

        for levy in self.nodes.levies.values():
            levy.calculate_expectation(
                self.nodes.emissions, emissions_lifetime, self.timeline, self._idx
            )

        for port in self.nodes.ports.values():
            port.calculate_expectation(self.timeline, self._idx)

        for producer in self.nodes.producers.values():
            calculate_export_expectation(producer, self.timeline, self._idx)

        for regulation in self.nodes.regulations.values():
            regulation.calculate_expectation(
                self.nodes.emissions,
                self.nodes.vessels,
                emissions_lifetime,
                self.timeline,
                self._idx,
            )

        for vessel in self.nodes.vessels.values():
            vessel.calculate_expectation(self._idx)

    def _calculate_vessel_operational_profile(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            allow_speed_management = fleet.allow_speed_management

            for vessel in fleet.vessels:
                update_operational_profile(vessel, allow_speed_management, self._idx)

        self.profile.add_vessel_time(timeit.default_timer() - start_time, self._idx)

    def _calculate_fuel_production_properties(self) -> None:
        start_time = timeit.default_timer()

        for plant in self.nodes.plants.values():
            # the feed masses are summed over the plant's process tree into every
            # step from this one on, so they are cleared before each recalculation
            plant.expectation.reset_additive_properties(self._idx)
            calculate_plant_production_expectations(
                plant, self.nodes.emissions, self.timeline, self._idx
            )

        self.profile.add_fuel_supply_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _calculate_fuel_logistics_properties(self) -> None:
        start_time = timeit.default_timer()

        calculate_plant_logistics_expectations(
            self.nodes.plants,
            self.nodes.ports,
            self.nodes.emissions,
            self.timeline,
            self._idx,
        )

        self.profile.add_fuel_supply_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _calculate_fuel_import(self) -> None:
        start_time = timeit.default_timer()

        calculate_fuel_import_to_ports(
            self.nodes.ports,
            self.nodes.producers,
            self.nodes.emissions,
            self.nodes.fuels,
            self.timeline,
            self._idx,
        )

        self.profile.add_fuel_supply_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _calculate_policy_emission_coefficients(self) -> None:
        start_time = timeit.default_timer()

        calculate_policy_emission_coefficients(
            self.nodes.regulations,
            self.nodes.levies,
            self.nodes.vessels,
            self.nodes.plants,
            self.timeline,
            self._idx,
        )

        self.profile.add_policy_time(timeit.default_timer() - start_time, self._idx)

    def _calculate_fair_share_fuel_supply(self, scope: BunkerScopeID) -> None:
        start_time = timeit.default_timer()

        fuels = {
            fuel_name: fuel
            for fuel_name, fuel in self.nodes.fuels.items()
            if not fuel.liquid_market
        }
        calculate_fair_share_fuel_supply(
            self.nodes.fleets, fuels, self.nodes.ports, self._idx, scope
        )

        self.profile.add_policy_time(timeit.default_timer() - start_time, self._idx)

    def _perform_producer_evolution(self) -> None:
        """
        Progress each producer in time and assign fair shares of the supply gap.

        The preparation per producer consists of:
        - updating increment ages,
        - delivering from the pipeline,
        - calculating feedstock gap.

        Then the fuel/supply demand gap is calculated and producers are assigned a
        fair-share of the gap and their pipeline is updated.
        """
        start_time = timeit.default_timer()

        fuels = {
            fuel_name: fuel
            for fuel_name, fuel in self.nodes.fuels.items()
            if not fuel.liquid_market
        }

        for producer in self.nodes.producers.values():
            perform_progression(producer, self.timeline, self._idx)
            calculate_development_potential(producer, self._time_step, self._idx)

        demand = calculate_expected_fuel_demand(self.nodes.fleets, self._idx)
        supply = calculate_expected_fuel_supply(self.nodes.producers, self._idx)
        gap = calculate_fuel_supply_demand_gap(fuels, supply, demand)
        calculate_constrained_fair_share_fuel_demand(
            fuels, self.nodes.producers, gap, self._idx
        )

        for producer in self.nodes.producers.values():
            perform_planning(producer, self.timeline, self._time_step, self._idx)

        self.profile.add_producer_evolution_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _update_increment_ages(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            fleet.update_increment_ages(self._time_step)

        for producer in self.nodes.producers.values():
            producer.update_increment_ages(self._time_step)

        self.profile.add_fleet_state_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _update_fleet_evolution_expectation(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            calculate_evolution_expectation(fleet, self.timeline, self._idx)

        self.profile.add_fleet_state_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _verify_power_capacity(self, scope: BunkerScopeID) -> None:
        """
        Verify converter power capacity for every vessel entering a bunkering scope.

        Mirrors the multiplier gating of BunkerAlgorithm.build: only vessels with a
        positive multiplier enter the LP. Expected bunkering builds one LP per future
        time-step, each gated by that step's expected multiplier; the demands and
        times it reads are constant over the remaining horizon within a time-step,
        so gating on the horizon maximum covers every one of those builds.

        Parameters
        ----------
        scope
            Bunkering scope about to be solved.
        """
        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                if scope == BunkerScopeID.EXISTING:
                    multiplier = fleet.expectation.get_existing_multipliers(
                        vessel.name, self._idx
                    )
                else:
                    multiplier = np.max(
                        fleet.expectation.get_expected_multipliers(
                            vessel.name, slice(self._idx, None)
                        )
                    )

                if multiplier > 0.0:
                    verify_power_capacity(vessel, self._idx)

    def _calculate_expected_bunkering(self) -> None:
        for vessel in self.nodes.vessels.values():
            vessel.expectation.reset_expected_bunkering()

        for regulation in self.nodes.regulations.values():
            regulation.expectation.reset_expected_bunkering()

        for i in range(self._idx, self.timeline.size):
            time_step_i = self.timeline[i] - self.timeline[i - 1]

            self._bunker_expected.build(self._idx, i, self.timeline[i], time_step_i)
            self._bunker_expected.solve()
            self._bunker_expected.transfer()

            self.profile.add_expected_build_time(
                self._bunker_expected.build_time, self._idx
            )
            self.profile.add_expected_solve_time(
                self._bunker_expected.solve_time, self._idx
            )
            self.profile.add_expected_transfer_time(
                self._bunker_expected.transfer_time, self._idx
            )

    def _update_scarcity_signals(self) -> None:
        start_time = timeit.default_timer()

        update_vessel_scarcity_beliefs(self.nodes.fleets, self.timeline, self._idx)
        update_regulation_flexibility_beliefs(
            self.nodes.regulations, self.nodes.vessels, self.timeline, self._idx
        )
        record_investment_signals(self.nodes.fleets, self._idx)

        self.profile.add_overhead_time(timeit.default_timer() - start_time, self._idx)

    def _perform_fleet_speed_management(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            perform_speed_management(fleet, self._time_step, self._idx)

        self.profile.set_speed_time(self._idx, timeit.default_timer() - start_time)

    def _perform_fleet_technology_installation(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            perform_technology_installation(
                fleet, self.timeline, self._time_step, self._idx
            )

        self.profile.set_retrofit_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_vessel_charter_properties(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                calculate_vessel_charter_properties(vessel, self.timeline, self._idx)

        self.profile.add_vessel_time(timeit.default_timer() - start_time, self._idx)

    def _calculate_cargo_charter_properties(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            for vessel in fleet.vessels:
                calculate_cargo_charter_properties(vessel, self.timeline, self._idx)

        self.profile.add_vessel_time(timeit.default_timer() - start_time, self._idx)

    def _perform_fleet_evolution(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            perform_fleet_evolution(fleet, self.timeline, self._time_step, self._idx)

        self.profile.add_fleet_evolution_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _perform_existing_bunkering(self) -> None:
        self._bunker_existing.build(self._idx, self._idx, self._time, self._time_step)
        self._bunker_existing.solve()
        self._bunker_existing.transfer()

        self.profile.set_existing_build_time(
            self._idx, self._bunker_existing.build_time
        )
        self.profile.set_existing_solve_time(
            self._idx, self._bunker_existing.solve_time
        )
        self.profile.set_existing_transfer_time(
            self._idx, self._bunker_existing.transfer_time
        )

    def _missing_technology_approximation(self) -> None:
        """
        Estimate energy-efficiency uptake for fleets that cannot retrofit.

        The estimate uses the fleet-average savings of the fleets that have them.
        """
        start_time = timeit.default_timer()

        approximate_missing_technology(self.nodes.fleets, self._idx)

        self.profile.add_fleet_state_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _initialize_bunker_models(self) -> None:
        # the solver backend is chosen before any model is created
        set_solver_preference(self.general_nodes.bunker_options.solver)

        self._bunker_existing.initialize(
            self.nodes.emissions,
            self.nodes.feedstocks,
            self.nodes.fleets,
            self.nodes.fuels,
            self.nodes.levies,
            self.nodes.ports,
            self.nodes.regulations,
            self.general_nodes.bunker_options,
            BunkerScopeID.EXISTING,
            output_directory=self.deck_directory,
        )
        self._bunker_expected.initialize(
            self.nodes.emissions,
            self.nodes.feedstocks,
            self.nodes.fleets,
            self.nodes.fuels,
            self.nodes.levies,
            self.nodes.ports,
            self.nodes.regulations,
            self.general_nodes.bunker_options,
            BunkerScopeID.EXPECTED,
            output_directory=self.deck_directory,
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
            regulation.initialize_expectation(length, self.nodes.vessels)

        for vessel in self.nodes.vessels.values():
            vessel.initialize_expectation(length, self.nodes.fuels)

    def _initialize_profiles(self) -> None:
        timeline = self.timeline / YEAR
        emissions_lifetime = self.general_nodes.model_definition.emissions_lifetime

        regulation_names = list(self.nodes.regulations.keys())
        levy_names = list(self.nodes.levies.keys())

        self.profile.initialize(
            timeline,
            self.nodes.emissions,
            self.nodes.feedstocks,
            self.nodes.fuels,
            self.nodes.processes,
            emissions_lifetime,
            regulation_names,
            levy_names,
        )

        for fleet in self.nodes.fleets.values():
            fleet.initialize_profile(
                timeline,
                self.nodes.fuels,
                self.nodes.emissions,
                emissions_lifetime,
                regulation_names,
                levy_names,
            )

        for levy in self.nodes.levies.values():
            levy.initialize_profile(timeline)

        for plant in self.nodes.plants.values():
            plant.initialize_profile(
                timeline, self.nodes.emissions, self.nodes.fuels, emissions_lifetime
            )

        for port in self.nodes.ports.values():
            port.initialize_profile(
                timeline, self.nodes.emissions, self.nodes.fuels, emissions_lifetime
            )

        for producer in self.nodes.producers.values():
            producer.initialize_profile(
                timeline, self.nodes.feedstocks, self.nodes.fuels, self.nodes.processes
            )

        for regulation in self.nodes.regulations.values():
            regulation.initialize_profile(timeline, self.nodes.vessels)

        for vessel in self.nodes.vessels.values():
            vessel.initialize_profile(
                timeline,
                self.nodes.emissions,
                self.nodes.fuels,
                emissions_lifetime,
                regulation_names,
                levy_names,
            )

    def _initialize_existing_fleet(self) -> None:
        fuel_by_fuel_type = get_fuels_per_fuel_type(self.nodes.fuels)

        for vessel in self.nodes.vessels.values():
            determine_fuel_type(vessel)
            determine_usable_fuel_types(vessel)
            determine_usable_fuels(vessel, fuel_by_fuel_type)

        assign_vessels_to_fleets(self.nodes.fleets.values())

        for fleet in self.nodes.fleets.values():
            initialize_existing_fleet(fleet, self.timeline)

    def _initialize_existing_production(self) -> None:
        for producer in self.nodes.producers.values():
            initialize_existing_producer(producer, self.timeline)

    def _calculate_profile(self) -> None:
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            calculate_fleet_profile(fleet, self.nodes.fuels, self.timeline, self._idx)

        for port in self.nodes.ports.values():
            port.calculate_profile(self._idx)

        for producer in self.nodes.producers.values():
            calculate_producer_profile(producer, self.timeline, self._idx)

        for regulation in self.nodes.regulations.values():
            regulation.calculate_profile(self._idx)

        for vessel in self.nodes.vessels.values():
            vessel.calculate_profile(self._idx)

        self.profile.add_profile_agg_time(
            timeit.default_timer() - start_time, self._idx
        )

    def _post_process(self) -> None:
        log_model_post_process(logger)

        # fold the recorded multipliers into the fleet output profiles before
        # the investment metric reads the in-fleet windows and before the
        # fleet profiles are merged into the global profile
        post_process_fleet_profile(self.nodes.fleets)
        post_process_investment_metric(self.nodes.fleets, self.timeline)

        for fleet in self.nodes.fleets.values():
            self.profile.add_fuel_consumer_profile(fleet.profile)
            self.profile.add_vessel_aggregate_profile(fleet.profile)

        for port in self.nodes.ports.values():
            self.profile.add_fuel_infrastructure_profile(port.profile)

        for producer in self.nodes.producers.values():
            self.profile.add_fuel_producer_profile(producer.profile)
            self.profile.add_plant_aggregate_profile(producer.profile)

    def _export_reports(self) -> None:
        for report in self.nodes.reports.values():
            write_report(report, self.results, self.deck_directory, self.deck_name)

    def get_elapsed_time(self) -> str:
        """
        Format the wall-clock time since the run started.

        Returns
        -------
        str
            The elapsed time in whole minutes and seconds.
        """
        return _write_elapsed_time(timeit.default_timer() - self._computational_time)

    def export_graphs(self) -> None:
        """Render the plots every Plot node of the deck requests."""
        # deferred so matplotlib only loads when plots are actually rendered
        from navigate.output.plots.render import generate_plots

        for plot_node in self.nodes.plots.values():
            generate_plots(plot_node, self.results, self.deck_directory)


def _write_elapsed_time(elapsed: float) -> str:
    minutes = math.floor(elapsed / 60.0)
    seconds = int(elapsed - minutes * 60.0)

    return f"elapsed time: {minutes}m and {seconds}s"
