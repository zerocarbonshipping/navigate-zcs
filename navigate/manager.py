# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import argparse
import logging
import math
import timeit
from pathlib import Path

import numpy as np

from navigate.bunker import BunkerAlgorithm
from navigate.core.enum_ import BunkerScopeID, EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.misc import YEAR
from navigate.core.profiles import ManagerProfile
from navigate.fuel import (
    calculate_plant_logistics_expectations,
    calculate_plant_production_expectations,
)
from navigate.fuel.producer.producer_profile import calculate_profile as calculate_producer_profile
from navigate.fuel.producer.producer_utils import calculate_development_potential
from navigate.fuel.supply_demand import (
    calculate_constrained_fair_share_fuel_demand,
    calculate_expected_fuel_demand,
    calculate_expected_fuel_supply,
    calculate_fuel_supply_demand_gap,
)
from navigate.investment.post_process import post_process_investment_metric
from navigate.investment.signal import (
    record_investment_signals,
    update_regulation_flexibility_beliefs,
    update_vessel_scarcity_beliefs,
)
from navigate.output import export_assumptions, log_model_post_process, log_start_of_simulation
from navigate.output.plot_data import PlotData
from navigate.parser import Parser
from navigate.policy import calculate_policy_emission_coefficients
from navigate.route.import_export import calculate_fuel_import_to_ports
from navigate.route.operation import convert_to_regional_steps, update_operational_profile
from navigate.route.speed import perform_speed_management
from navigate.util import dates_to_days, timedelta_to_days
from navigate.vessel.charter import calculate_cargo_charter_properties, calculate_vessel_charter_properties
from navigate.vessel.fair_share_fuel import calculate_fair_share_fuel_supply
from navigate.vessel.fleet import fleet_evolution
from navigate.vessel.fleet import fleet_profile as fleet_profile_mod
from navigate.vessel.fleet.fleet_technology import perform_technology_installation
from navigate.vessel.fleet.fleet_utils import net_energy_from_raw
from navigate.vessel.fuel_option import (
    determine_fuel_type,
    determine_usable_fuel_types,
    determine_usable_fuels,
    get_fuels_per_fuel_type,
)

logger = logging.getLogger(__name__)


class SimulationManager:
    def __init__(self):

        # properties ---------------------------------------------------------------------------------------------------
        self._time_step = 0.        # float, size of current time-step, days
        self._time = 0.             # float, time since start of simulation, days
        self._date = None           # np.datetime64, current date
        self._idx = 0               # int, time-step index

        # simulation time/date line
        self._timeline = None       # np.ndarray, all times at which the simulation will perform calculations, days
        self._dateline = None       # np.ndarray, all dates at which the simulation will perform calculations,

        # profile
        self.profile = ManagerProfile()

        # bunker algorithm ---------------------------------------------------------------------------------------------
        self._bunker_existing: BunkerAlgorithm | None = None    # BunkerAlgorithm
        self._bunker_expected: BunkerAlgorithm | None = None    # BunkerAlgorithm

        # parser -------------------------------------------------------------------------------------------------------
        self._parser = Parser()
        self.nodes = self._parser.nodes
        self.general_nodes = self._parser.general_nodes

        # code timing --------------------------------------------------------------------------------------------------
        self._computational_time = None

    def read_deck(self, path: Path, args: argparse.Namespace) -> None:
        """
        Read the simulation deck using the Parser. Must be called prior to the 'run' method.

        Parameters
        ----------
        path
            Path to the simulation deck.
        args
            Command line arguments parsed by the CLI.
        """

        # read the simulation deck
        self._parser.read_deck(path, data_dir=args.data_dir)

        # apply CLI solver override (takes precedence over deck setting)
        if getattr(args, "solver", None) is not None:
            self.general_nodes.bunker_options.set_solver(args.solver.upper())

    def run(self):
        """
        Run the simulation as defined in the deck. This method handles the high-level flow of the simulation.
        """

        # check that necessary nodes are
        # defined as well as a timeline
        self._parser.includes_necessary_information()

        # start computational time
        self._computational_time = timeit.default_timer()

        # initialize the simulation
        self._initialize_timeline()
        self._initialize_simulation()

        # perform time-stepping
        self._run_simulation()

        # post process and export reports
        self._post_process()
        self._export_reports()
        self._export_plot_data()

        print("Finished simulation, {}.".format(self.get_elapsed_time()))

    def _initialize_timeline(self):
        """
        All dates at which the simulation will perform calculations is known up front once the Parser has read
        the input deck. This method initializes all time-related properties on the Manager required for calculations
        throughout the simulation.

        """

        self._dateline = self._parser.get_dates()
        self._timeline = dates_to_days(self._dateline)

        # initial time/date and index
        self._idx = 0
        self._time = 0.
        self._date = self.general_nodes.model_definition.get_start_date()

    def _initialize_simulation(self):
        """
        This method initializes the model based on the defined initial conditions.
        The calculations performed overlap partially with those performed at each time-step.
        """

        # log the start of the simulation
        # to the .log file
        log_start_of_simulation(logger, self._date)

        # initialize expectations on
        # all nodes which will store
        # intermediate calculation results
        self._initialize_expectations()

        # initialize the profiles on
        # all nodes which will store
        # simulation results
        self._initialize_profiles()

        # initialize the existing bunkering
        # model as well as the individual
        # vessel models used to calculate
        # expected fuel expenses
        self._initialize_bunker_models()

        # read the initial time-step
        # from the event queue for
        # what happens at 'Start'
        date = self._parser.progress_timeline()
        self._progress_date_time(date)

        # perform calculations related
        # to the initial time-step of
        # the model
        self._perform_time_step()

        # progress time-step index
        self._idx += 1

    def _run_simulation(self):

        # read the first date after initialization
        date = self._parser.progress_timeline()

        # time-stepping loop
        while date:

            # update current time information
            self._progress_date_time(date)

            # calculate the state of the
            # simulation at the current date
            self._perform_time_step()

            # progress to the next
            # date and read events
            date = self._parser.progress_timeline()
            self._idx += 1

    def _progress_date_time(self, date):
        self._time_step = timedelta_to_days(date - self._date)
        self._time += self._time_step
        self._date = date

        # for the few methods which are called
        # during the initialization of the model,
        # but require time-step sizes, assume it
        # is one year
        if self._idx == 0:
            self._time_step = YEAR

    def _perform_time_step(self):

        # print current date to window
        # for convenience to follow
        # progress of simulation
        print('Date: {}'.format(self._date))

        # temporal calculators are have time
        # assigned or precalculated value for
        # convenience to allow direct access
        # via .get() without having to pass
        # time to all methods
        start_time = timeit.default_timer()
        self._pre_assign_temporal()

        # precalculate certain expectations
        # which are simulation bottlenecks
        self._calculate_expectations()
        self.profile.add_temporal_time(self._idx, timeit.default_timer() - start_time)

        # calculate the raw energy demand
        # and trade carrying capacity of
        # all vessels in the fleet
        self._calculate_vessel_operational_profile()

        # calculate the costs and emissions
        # related with the production of fuels
        self._calculate_fuel_production_properties()

        # calculate the costs and emissions
        # related with the transport of fuels
        self._calculate_fuel_logistics_properties()

        if self._idx == 0:

            # initialize the existing fleet based
            # on the defined initial conditions
            start_time_overhead = timeit.default_timer()
            self._initialize_existing_fleet()

            # initialize the existing production based
            # on the defined initial conditions
            self._initialize_existing_production()
            self.profile.add_overhead_time(self._idx, timeit.default_timer() - start_time_overhead)

        # calculate the chartering costs of all vessels in the fleet.
        # Technology costs are excluded here: they enter the cargo charter
        # metrics below as the fleet-average carried technology charge
        self._calculate_vessel_charter_properties()

        if self._idx > 0:

            # update the age of the fleets and producers
            # prior to performing calculations which depends
            # on the existing fleet/capacity
            self._update_increment_ages()

            # update fleet evolution expectations prior
            # to expected bunkering to ensure vessels
            # that have been allowed in the current
            # time-step have a non-zero multiplier
            self._update_fleet_evolution_expectation()

            # calculate the fair-share of the fuel
            # supply for each individual vessel
            self._calculate_fair_share_fuel_supply(BunkerScopeID.EXPECTED)

            # calculate the policy emission coefficients
            self._calculate_policy_emission_coefficients(BunkerScopeID.EXPECTED)

            # calculate the expected bunkering
            # for every vessel given current
            # availability outlook
            self._calculate_expected_bunkering()

            # smooth the energy-conservation LP duals into
            # scarcity belief paths consumed by the technology
            # and speed-management heuristics below
            self._update_scarcity_signals()

            # perform the technology retrofit for
            # every fleet based on the expected
            # fuel expenses
            self._perform_fleet_technology_installation()

            # calculate speed management for every
            # fleet based on the expected fuel
            # expenses
            self._perform_fleet_speed_management()

            # calculate the freight costs for every
            # vessel in the fleet which is used to
            # determine the uptake of different
            # vessel types
            self._calculate_cargo_charter_properties()

            # calculate the evolution of the fleet
            # based on scrapping, fuel conversions
            # and newbuilds
            self._perform_fleet_evolution()

            # perform an evolution of the producers
            # based on decommissioning and newbuilds
            # from the pipeline
            self._perform_producer_evolution()

        # estimate reasonable energy efficiency
        # uptake in vessel segments which do not
        # have energy saving technology assumptions
        # available to them
        self._missing_technology_approximation()

        # calculate the export from producers
        # and import in ports of bunker fuel
        self._calculate_fuel_import()

        # calculate the fair-share of the fuel
        # supply for each individual vessel
        self._calculate_fair_share_fuel_supply(BunkerScopeID.EXISTING)

        # calculate the policy emission coefficients
        self._calculate_policy_emission_coefficients(BunkerScopeID.EXISTING)

        # solve the bunkering for all vessels
        # simultaneously, taking into account
        # fuel availability constraints
        self._perform_existing_bunkering()

        # transfer internal results and
        # calculate derived results based on
        # the results of the simulation
        self._calculate_profile()

        # set computational performance trackers
        self.profile.set_total_time(self._idx, timeit.default_timer() - self._computational_time)

    def _pre_assign_temporal(self):
        """
        Precalculate forecasts and assign time to timetables.
        """

        for forecast in self.nodes.forecasts.values():
            forecast.precalculate(self._time)

        for timetable in self.nodes.timetables.values():
            timetable.set_current_time(self._time)

    def _calculate_expectations(self):
        """
        Precalculate certain expectations which are simulation bottlenecks
        """

        emissions_lifetime = self.general_nodes.model_definition.get_emissions_lifetime()

        for levy in self.nodes.levies.values():
            levy.calculate_expectation(self.nodes.emissions, emissions_lifetime, self._timeline, self._idx)

        for port in self.nodes.ports.values():
            port.calculate_expectation(self._timeline, self._idx)

        for producer in self.nodes.producers.values():
            producer.calculate_expectation(self._timeline, self._idx)

        for regulation in self.nodes.regulations.values():
            regulation.calculate_expectation(self.nodes.emissions,
                                             self.nodes.vessels,
                                             emissions_lifetime, self._timeline, self._idx)

        for vessel in self.nodes.vessels.values():
            vessel.calculate_expectation(self._idx)

    def _calculate_vessel_operational_profile(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():

            allow_speed_management = fleet.allow_speed_management

            for vessel in fleet.get_vessels():
                update_operational_profile(vessel, allow_speed_management, self._idx)

        self.profile.add_vessel_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_fuel_production_properties(self):
        start_time = timeit.default_timer()

        # calculate properties for each plant
        for plant in self.nodes.plants.values():

            # need to reset additive properties prior to calculating
            plant.expectation.reset_additive_properties(self._idx)
            calculate_plant_production_expectations(plant, self.nodes.emissions, self._timeline, self._idx)

        self.profile.add_fuel_supply_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_fuel_logistics_properties(self):
        start_time = timeit.default_timer()

        calculate_plant_logistics_expectations(self.nodes.plants,
                                               self.nodes.ports,
                                               self.nodes.emissions,
                                               self.general_nodes.bunker_logistics,
                                               self._timeline,
                                               self._idx)

        self.profile.add_fuel_supply_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_fuel_import(self):
        start_time = timeit.default_timer()

        calculate_fuel_import_to_ports(self.nodes.ports,
                                       self.nodes.producers,
                                       self.nodes.emissions,
                                       self.nodes.fuels,
                                       self.nodes.routes,
                                       self._timeline,
                                       self._idx)

        self.profile.add_fuel_supply_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_policy_emission_coefficients(self, bunker_scope):
        start_time = timeit.default_timer()

        calculate_policy_emission_coefficients(self.nodes.regulations,
                                               self.nodes.levies,
                                               self.nodes.vessels,
                                               bunker_scope,
                                               self._timeline,
                                               self._idx)

        self.profile.add_policy_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_fair_share_fuel_supply(self, scope):
        start_time = timeit.default_timer()

        fuels = {fuel_name: fuel for fuel_name, fuel in self.nodes.fuels.items() if not fuel.belongs_to_liquid_market()}
        calculate_fair_share_fuel_supply(self.nodes.fleets, fuels, self.nodes.ports, self._idx, scope)

        self.profile.add_policy_time(self._idx, timeit.default_timer() - start_time)

    def _perform_producer_evolution(self):
        """
        As preparation each producer is progressed in time, namely:
        - updating increment ages,
        - delivering from the pipeline,
        - calculating feedstock gap.

        Then the fuel/supply demand gap is calculated and producers are assigned a fair-share of the gap and their
        pipeline is updated.
        """

        start_time = timeit.default_timer()

        # extract all fuels not belonging to a liquid market
        fuels = {key: value for key, value in self.nodes.fuels.items() if not value.belongs_to_liquid_market()}

        # update the existing production and
        # calculate development potential
        for producer in self.nodes.producers.values():
            producer.perform_progression(self._timeline, self._time_step, self._idx)
            calculate_development_potential(producer, self._time_step, self._idx)

        # calculate the expected fuel demand once as
        # it remains constant across the two passes
        demand = calculate_expected_fuel_demand(self.nodes.fleets, self._idx)

        # perform 1st pass (constrained)
        supply = calculate_expected_fuel_supply(self.nodes.producers, self._idx)
        gap = calculate_fuel_supply_demand_gap(fuels, supply, demand)
        calculate_constrained_fair_share_fuel_demand(fuels, self.nodes.producers, gap, self._idx)

        for producer in self.nodes.producers.values():
            producer.perform_planning(self._timeline, self._time_step, self._idx)

        # set computational performance tracker
        self.profile.add_producer_evolution_time(self._idx, timeit.default_timer() - start_time)

    def _update_increment_ages(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            fleet.update_increment_ages(self._time_step)

        for producer in self.nodes.producers.values():
            producer.update_increment_ages(self._time_step)

        self.profile.add_fleet_state_time(self._idx, timeit.default_timer() - start_time)

    def _update_fleet_evolution_expectation(self):
        start_time = timeit.default_timer()

        # update fleet evolution expectations prior
        # to expected bunkering to ensure vessels
        # that have been allowed in the current
        # time-step have a non-zero multiplier
        for fleet in self.nodes.fleets.values():
            fleet_evolution.calculate_evolution_expectation(fleet, self._idx, self._timeline)

        self.profile.add_fleet_state_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_expected_bunkering(self):

        # reset the expected bunkering solutions
        for vessel in self.nodes.vessels.values():
            vessel.expectation.reset_expected_bunkering()

        for regulation in self.nodes.regulations.values():
            regulation.expectation.reset_expected_bunkering()

        future_indices = range(self._idx, self._timeline.size)

        for i in future_indices:

            time_step_i = self._timeline[i] - self._timeline[i - 1]

            self._bunker_expected.build(self._idx, i, self._timeline[i], time_step_i)
            self._bunker_expected.solve()
            self._bunker_expected.transfer()

            # set computational performance tracker
            self.profile.add_expected_build_time(self._idx, self._bunker_expected.get_build_time())
            self.profile.add_expected_solve_time(self._idx, self._bunker_expected.get_solve_time())
            self.profile.add_expected_transfer_time(self._idx, self._bunker_expected.get_transfer_time())

    def _update_scarcity_signals(self):
        start_time = timeit.default_timer()

        update_vessel_scarcity_beliefs(self.nodes.fleets, self._timeline, self._idx)
        update_regulation_flexibility_beliefs(self.nodes.regulations, self.nodes.vessels, self._timeline, self._idx)
        record_investment_signals(self.nodes.fleets, self._idx)

        self.profile.add_overhead_time(self._idx, timeit.default_timer() - start_time)

    def _perform_fleet_speed_management(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            perform_speed_management(fleet, self._time_step, self._idx)

        # set computational performance tracker
        self.profile.set_speed_time(self._idx, timeit.default_timer() - start_time)

    def _perform_fleet_technology_installation(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            perform_technology_installation(fleet, self._timeline, self._time_step, self._idx)

        # set computational performance tracker
        self.profile.set_retrofit_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_vessel_charter_properties(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            for vessel in fleet.get_vessels():
                calculate_vessel_charter_properties(vessel, self._timeline, self._idx)

        self.profile.add_vessel_time(self._idx, timeit.default_timer() - start_time)

    def _calculate_cargo_charter_properties(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            for vessel in fleet.get_vessels():
                calculate_cargo_charter_properties(vessel, self._timeline, self._idx)

        self.profile.add_vessel_time(self._idx, timeit.default_timer() - start_time)

    def _perform_fleet_evolution(self):
        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():

            fleet_evolution.perform_fleet_evolution(
                fleet, self._timeline, self._time_step, self._idx)

        # set computational performance tracker
        self.profile.add_fleet_evolution_time(self._idx, timeit.default_timer() - start_time)

    def _perform_existing_bunkering(self):

        self._bunker_existing.build(self._idx, self._idx, self._time, self._time_step)
        self._bunker_existing.solve()
        self._bunker_existing.transfer()

        # set computational performance tracker
        self.profile.set_existing_build_time(self._idx, self._bunker_existing.get_build_time())
        self.profile.set_existing_solve_time(self._idx, self._bunker_existing.get_solve_time())
        self.profile.set_existing_transfer_time(self._idx, self._bunker_existing.get_transfer_time())

    def _missing_technology_approximation(self):
        """
        Estimates missing energy efficiency improvements for fleets and vessels, applies these
        approximations to energy demands for both sea and port operations, and updates associated
        vessel profiles and expectations.

        The method pulls from vessels that can retrofit technologies and applies the average over
        the fleet's vessels to estimate energy efficiency improvements.

        Costs are ignored in this calculation, so we underestimate the costs of energy efficiency improvements.
        """
        start_time = timeit.default_timer()

        average_energy_saving_sea = {energy: 0. for energy in EnergyDemandTypeID}
        average_energy_saving_port = {energy: 0. for energy in EnergyDemandTypePortID}

        weight_sea = {k: 0.0 for k in average_energy_saving_sea}
        weight_port = {k: 0.0 for k in average_energy_saving_port}

        for fleet in self.nodes.fleets.values():
            if not fleet.can_retrofit():
                continue

            vessels = fleet.get_vessels()
            for v, vessel in enumerate(vessels):
                multiplier = fleet.get_multiplier(v)
                expectation = vessel.expectation

                raw_energy_sea = expectation.get_raw_energy_sea(idx=self._idx)
                raw_energy_port = expectation.get_raw_energy_port(idx=self._idx)
                savings_sea = expectation.get_energy_saving_sea(idx=self._idx)
                savings_port = expectation.get_energy_saving_port(idx=self._idx)

                for k in average_energy_saving_sea:
                    for leg, _ in enumerate(raw_energy_sea[k]):
                        weight = raw_energy_sea[k][leg] * multiplier
                        average_energy_saving_sea[k] += savings_sea[k][leg] * weight
                        weight_sea[k] += weight
                for k in average_energy_saving_port:
                    for leg, _ in enumerate(raw_energy_port[k]):
                        weight = raw_energy_port[k][leg] * multiplier
                        average_energy_saving_port[k] += savings_port[k][leg] * weight
                        weight_port[k] += weight

        for k in average_energy_saving_sea:
            average_energy_saving_sea[k] = (average_energy_saving_sea[k] / weight_sea[k]) if weight_sea[k] else 0.0
        for k in average_energy_saving_port:
            average_energy_saving_port[k] = (average_energy_saving_port[k] / weight_port[k]) if weight_port[k] else 0.0

        for fleet in self.nodes.fleets.values():
            if fleet.can_retrofit() or not fleet.allow_technology_approximation:
                continue
            for vessel in fleet.get_vessels():
                op_sea = vessel.expectation.get_operational_energy_sea(idx=self._idx)
                op_port = vessel.expectation.get_operational_energy_port(idx=self._idx)

                sav_sea = {k: [average_energy_saving_sea[k]] * len(op_sea[k])
                           for k in average_energy_saving_sea if k in op_sea}

                sav_port = {k: [average_energy_saving_port[k]] * len(op_port[k])
                            for k in average_energy_saving_port if k in op_port}

                net_sea = net_energy_from_raw(op_sea, sav_sea)
                net_port = net_energy_from_raw(op_port, sav_port)
                regional_sea = convert_to_regional_steps(vessel, net_sea)

                vessel.expectation.set_energy_sea(self._idx, net_sea)
                vessel.expectation.set_energy_port(self._idx, net_port)
                vessel.expectation.set_regional_energy_sea(self._idx, regional_sea)

                vessel.profile.set_energy_sea(
                    self._idx, {k: float(np.sum(net_sea[k])) for k in net_sea}
                )
                vessel.profile.set_energy_port(
                    self._idx, {k: float(np.sum(net_port[k])) for k in net_port}
                )

        self.profile.add_fleet_state_time(self._idx, timeit.default_timer() - start_time)

    def _initialize_bunker_models(self):

        # configure solver backend before creating any models
        import navigate.bunker.solver as solver
        solver.set_solver_preference(self.general_nodes.bunker_options.get_solver())

        # initialize BunkerAlgorithm for existing bunkering
        self._bunker_existing = BunkerAlgorithm()
        self._bunker_existing.initialize(self.nodes.emissions,
                                         self.nodes.feedstocks,
                                         self.nodes.fleets,
                                         self.nodes.fuels,
                                         self.nodes.levies,
                                         self.nodes.ports,
                                         self.nodes.regulations,
                                         self.general_nodes.bunker_options,
                                         BunkerScopeID.EXISTING,
                                         output_directory=self._parser.get_deck_directory())

        # initialize a BunkerAlgorithm for expected bunkering
        self._bunker_expected = BunkerAlgorithm()
        self._bunker_expected.initialize(self.nodes.emissions,
                                         self.nodes.feedstocks,
                                         self.nodes.fleets,
                                         self.nodes.fuels,
                                         self.nodes.levies,
                                         self.nodes.ports,
                                         self.nodes.regulations,
                                         self.general_nodes.bunker_options,
                                         BunkerScopeID.EXPECTED,
                                         output_directory=self._parser.get_deck_directory())

    def _initialize_expectations(self):

        length = self._timeline.size

        for fleet in self.nodes.fleets.values():
            fleet.initialize_expectation(length, self.nodes.fuels)

        for levy in self.nodes.levies.values():
            levy.initialize_expectation(length)

        for plant in self.nodes.plants.values():
            plant.initialize_expectation(length,
                                         self.nodes.emissions,
                                         self.nodes.feedstocks,
                                         self.nodes.ports,
                                         self.nodes.processes)

        for port in self.nodes.ports.values():
            port.initialize_expectation(length, self.nodes.fuels, self.nodes.emissions)

        for producer in self.nodes.producers.values():
            producer.initialize_expectation(length,
                                            self.nodes.feedstocks,
                                            self.nodes.fuels,
                                            self.nodes.ports,
                                            self.nodes.processes)

        for regulation in self.nodes.regulations.values():
            regulation.initialize_expectation(length, self.nodes.vessels)

        for vessel in self.nodes.vessels.values():
            vessel.initialize_expectation(length, self.nodes.fuels)

    def _initialize_profiles(self):

        timeline = self._timeline / YEAR
        emissions_lifetime = self._parser.get_model_definition().get_emissions_lifetime()

        regulation_names = list(self.nodes.regulations.keys())
        levy_names = list(self.nodes.levies.keys())

        self.profile.initialize(timeline,
                                self.nodes.emissions,
                                self.nodes.feedstocks,
                                self.nodes.fuels,
                                self.nodes.processes,
                                emissions_lifetime,
                                regulation_names,
                                levy_names)

        for fleet in self.nodes.fleets.values():
            fleet.initialize_profile(timeline, self.nodes.fuels, self.nodes.emissions, emissions_lifetime,
                                     regulation_names, levy_names)

        for levy in self.nodes.levies.values():
            levy.initialize_profile(timeline)

        for plant in self.nodes.plants.values():
            plant.initialize_profile(timeline, self.nodes.emissions, emissions_lifetime)

        for port in self.nodes.ports.values():
            port.initialize_profile(timeline, self.nodes.emissions, self.nodes.fuels, emissions_lifetime)

        for producer in self.nodes.producers.values():
            producer.initialize_profile(timeline,
                                        self.nodes.feedstocks,
                                        self.nodes.fuels,
                                        self.nodes.processes)

        for regulation in self.nodes.regulations.values():
            regulation.initialize_profile(timeline, self.nodes.vessels)

        for vessel in self.nodes.vessels.values():
            vessel.initialize_profile(timeline, self.nodes.emissions, self.nodes.fuels, emissions_lifetime,
                                      regulation_names, levy_names)

    def _initialize_existing_fleet(self):

        # determine the possible fuels
        # usable by each vessel and store
        # them on the vessel as a convenience
        fuel_by_fuel_type = get_fuels_per_fuel_type(self.nodes.fuels)

        for vessel in self.nodes.vessels.values():

            determine_fuel_type(vessel)
            determine_usable_fuel_types(vessel)
            determine_usable_fuels(vessel, fuel_by_fuel_type)

        for fleet in self.nodes.fleets.values():
            fleet.initialize_existing_fleet(self._timeline)

        # loop over vessels and log a warning if
        # the plant is not assigned to any fleet
        for vessel in self.nodes.vessels.values():

            if not vessel.is_assigned_to_fleet():

                logger.warning("{}: Is not assigned to a 'Fleet' and consequently ignored during the simulation."
                               .format(vessel))

    def _initialize_existing_production(self):

        for producer in self.nodes.producers.values():
            producer.initialize_existing_producer(self._timeline)

        # loop over plants and log a warning if the
        # plant is not assigned to any producer
        for plant in self.nodes.plants.values():

            if not plant.is_assigned_to_producer():

                logger.warning("{}: Is not assigned to a 'Producer' and consequently ignored during the simulation."
                               .format(plant))

    def _calculate_profile(self):

        start_time = timeit.default_timer()

        for fleet in self.nodes.fleets.values():
            fleet_profile_mod.calculate_profile(fleet, self.nodes.fuels, self._timeline, self._idx)

        for port in self.nodes.ports.values():
            port.calculate_profile(self._idx)

        for producer in self.nodes.producers.values():
            calculate_producer_profile(producer, self._timeline, self._idx)

        for regulation in self.nodes.regulations.values():
            regulation.calculate_profile(self._idx)

        for vessel in self.nodes.vessels.values():
            vessel.calculate_profile(self._idx)

        self.profile.add_profile_agg_time(self._idx, timeit.default_timer() - start_time)

    def _post_process(self):

        log_model_post_process(logger)

        # post-process investment metrics
        post_process_investment_metric(self.nodes.fleets, self._timeline)

        # aggregate lower level profiles
        for fleet in self.nodes.fleets.values():

            # add all consumer related properties
            fleet_profile = fleet.profile
            self.profile.add_fuel_consumer_profile(fleet_profile)
            self.profile.add_vessel_aggregate_profile(fleet_profile)

        for port in self.nodes.ports.values():
            self.profile.add_fuel_infrastructure_profile(port.profile)
            self.profile.add_infrastructure_aggregate_profile(port.profile)

        for producer in self.nodes.producers.values():
            self.profile.add_fuel_producer_profile(producer.profile)
            self.profile.add_plant_aggregate_profile(producer.profile)

    def _export_reports(self):

        for report_name, report in self.nodes.reports.items():

            # Layer 3: Protect report initialization
            try:
                report.start_export()
            except Exception as e:
                logger.error("Report '%s': Failed to initialize, skipping: %s", report_name, e)
                continue

            # Layer 2: Protect each sheet export individually
            sheet_errors = 0
            for sheet_name, method_name, args in [
                ("manager",     "export_manager",      (self,)),
                ("fleets",      "export_fleets",       (self.nodes.fleets,)),
                ("levies",      "export_levies",       (self.nodes.levies,)),
                ("plants",      "export_plants",       (self.nodes.plants,)),
                ("ports",       "export_ports",        (self.nodes.ports,)),
                ("producers",   "export_producers",    (self.nodes.producers,)),
                ("regulations", "export_regulations",  (self.nodes.regulations,)),
                ("vessels",     "export_vessels",       (self.nodes.vessels,)),
            ]:
                try:
                    getattr(report, method_name)(*args)
                except Exception as e:
                    logger.error("Report '%s': Failed to export '%s': %s", report_name, sheet_name, e)
                    sheet_errors += 1

            # Layer 3: Protect file save
            try:
                report.end_export(self._parser.get_deck_directory(), self._parser.get_deck_name(), self._dateline)
            except Exception as e:
                logger.error("Report '%s': Failed to save file: %s", report_name, e)

            if sheet_errors:
                logger.warning("Report '%s': Completed with %d sheet error(s).", report_name, sheet_errors)

    def get_elapsed_time(self):
        return _write_elapsed_time(timeit.default_timer() - self._computational_time)

    def export_assumptions(self):
        export_assumptions(self)

    def _export_plot_data(self):
        plot_data = PlotData.from_manager(self)
        plot_data.save()

    def _export_plots(self, plot_data):
        for plot_node in self.nodes.plots.values():
            plot_node.generate_plots(plot_data)

    def export_graphs(self):
        plot_data = PlotData.from_manager(self)
        self._export_plots(plot_data)

    def get_time(self):
        return self._time

    def get_date(self):
        return self._date

    def get_parser(self):
        return self._parser

    def get_timeline(self):
        return self._timeline

    def get_dateline(self):
        return self._dateline

    @staticmethod
    def get_name():
        """
        This method is required for export of reports with manager properties.

        Returns
        -------
        str
            The default name of a simulation.
        """
        return 'global'


def _write_elapsed_time(elapsed):
    minutes = math.floor(elapsed / 60.)
    seconds = int(elapsed - minutes * 60.)

    return 'elapsed time: {}m and {}s'.format(minutes, seconds)
