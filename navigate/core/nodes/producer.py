# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    as_scalar_list,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
)
from navigate.core.enum_ import ExtrapolateID
from navigate.core.expectations import ProducerExpectation
from navigate.core.increment import Increment
from navigate.core.node_type import FORECAST, PLANT, PRODUCER, VARIABLE
from navigate.core.nodes._asset_manager import _AssetManager
from navigate.core.profiles import ProducerProfile
from navigate.exceptions import no_value_assigned_error
from navigate.fuel.evolution import (
    calculate_evolution_expectation,
    calculate_export_expectation,
    calculate_feed_availability,
    define_existing_pipeline,
    perform_decommissioning,
    perform_pipeline_delivery,
)
from navigate.fuel.planning import perform_pipeline_planning
from navigate.util import (
    YEAR,
    is_non_strictly_increasing,
)

if TYPE_CHECKING:
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process

logger = logging.getLogger(__name__)


class Producer(_AssetManager):
    def __init__(self, name):
        super().__init__(name, PRODUCER)

        # external properties ------------------------------------------------------------------------------------------

        # plant uptake
        self.minimum_offtake_duration = None   # float, minimum duration of offtake agreements, years
        self.fuel_demand_sensitivity = None    # float, odds ratio for pathway choice on expected demand
        self.fuel_cost_sensitivity = None      # float, odds ratio for plant choice on LCoF

        # initial conditions
        self._initial_capacity = []     # list[float], initial capacity per plant type, tons/day

        # existing pipeline
        self.existing_pipelines = {}   # dict[plant_name: Forecast]

        # constraints
        self.maximum_development = None    # float, number of plants which can be built per year
        self.feed_constraints = {}         # dict[float], amount of feed (process/feedstock) available for plants
        self.jump_start_fraction = None    # float, fraction to jump-start supply/demand interaction
        self.maximum_ramp_up = None        # float, maximum change in utilization of development, fraction/year

        # export
        self.export_distribution = {}  # dict[port_name: float], fraction of production being exported to which port

        # boolean
        self.allow_plant = {}  # dict[bool], whether a plant is allowed to be built

        # internal properties ------------------------------------------------------------------------------------------
        # pipeline increments (Producer-specific, separate from active increments in _AssetManager)
        self.pipeline: list[list[Increment]] = []

        # static properties
        self._initialized = False       # bool, true if the fleet has been initialized
        self.fuels = {}                # dict[Fuel], store a list of possible production fuels for convenience

        # dynamic properties
        self.current_utilization = None    # float, current fraction of construction capacity utilized

    # public domain name for the inherited assets list
    plants = property(lambda self: self.assets)

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_plants(self, plants):
        """
        Set the list of plant types that can be built.

        Examples
        --------
        - Plant("name")
        - [Plant("name1"), Plant("name2")]

        Parameters
        ----------
        plants : list[NodeReference]
            The list of plants that can be built.
        """

        self.assets = assign_list(as_list(plants), unique=True, scalar=False, type_=PLANT)

    def set_minimum_offtake_duration(self, minimum_offtake_duration):
        """
        Set the minimum offtake duration required for building new plants.

        Examples
        --------
        - 7
        - Forecast("name")

        Parameters
        ----------
        minimum_offtake_duration : float | NodeReference
            The minimum offtake agreement for building new plants.
        """

        self.minimum_offtake_duration = assign_value(as_scalar(minimum_offtake_duration), type_=(FORECAST, VARIABLE), lower=1.)

    def set_fuel_demand_sensitivity(self, fuel_demand_sensitivity):
        """
        Set the sensitivity of the fuel-pathway choice to expected demand.

        The value is an odds ratio: a pathway whose expected demand is 10% higher receives this many
        times the odds of an otherwise identical pathway. For example 1.25 means a 10% higher demand
        gives 1.25 times the odds, and 1 means no preference. Demand is higher-is-better, so use a
        value above 1.

        Examples
        --------
        - 1.25
        - Forecast("name")

        Parameters
        ----------
        fuel_demand_sensitivity : float | NodeReference
            Odds ratio for a 10% higher expected demand in the between-pathway choice.
        """

        self.fuel_demand_sensitivity = assign_value(as_scalar(fuel_demand_sensitivity), type_=(FORECAST, VARIABLE),
                                                    lower=0., inclusive_lower=False)

    def set_fuel_cost_sensitivity(self, fuel_cost_sensitivity):
        """
        Set the sensitivity of the plant choice to levelized cost of fuel (LCoF).

        The value is an odds ratio: a plant whose LCoF is 10% higher receives this many times the odds
        of an otherwise identical plant. For example 0.5 means a 10% higher LCoF halves the odds, and
        1 means no preference. LCoF is lower-is-better, so use a value below 1.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        fuel_cost_sensitivity : float | NodeReference
            Odds ratio for a 10% higher LCoF in the within-pathway plant choice.
        """

        self.fuel_cost_sensitivity = assign_value(as_scalar(fuel_cost_sensitivity), type_=(FORECAST, VARIABLE),
                                                  lower=0., inclusive_lower=False)

    def set_initial_capacity(self, initial_capacity):
        """
        Set the list of initial capacity for each plant type in tons/day.

        The list must have the same length as the list of plants.

        Examples
        --------
        - [Forecast("name"), 0]

        Parameters
        ----------
        initial_capacity : list[float]
            List of initial production in tons/day.
        """

        self._initial_capacity = assign_list(as_scalar_list(initial_capacity), type_=VARIABLE, lower=0.)

    def set_maximum_development(self, maximum_development):
        """
        Set the maximum development limiting the number of plants which can be built per year.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        maximum_development : float | NodeReference
            Maximum developments of plants per year.
        """

        self.maximum_development = assign_value(as_scalar(maximum_development), type_=(FORECAST, VARIABLE), lower=0.)

    def set_maximum_ramp_up(self, maximum_ramp_up):
        """
        Set the maximum ramp-up for the utilization of the development constraint per year.

        Examples
        --------
        - 0.2
        - Forecast("name")

        Parameters
        ----------
        maximum_ramp_up : float | NodeReference
            The maximum ramp-up for the utilization of the development constraint.
        """

        self.maximum_ramp_up = assign_value(as_scalar(maximum_ramp_up), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_jump_start_fraction(self, jump_start_fraction):
        """
        Set the jump-start fraction used to initiate the supply/demand interaction if there has been no production.

        Due to the use of self.current_uptake and self.current_utilization in the expectation calculations it is
        necessary to include a "jump-start" fraction in case those values are zero, to get the supply/demand interaction
        started.

        Examples
        --------
        - 0.1

        Parameters
        ----------
        jump_start_fraction : float | NodeReference
            The jump-start fraction for supply/demand interaction.
        """

        self.jump_start_fraction = assign_value(jump_start_fraction, lower=0., upper=1.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_existing_pipeline(self, plant_name, existing_pipeline):
        """
        Set an existing pipelines for a given plant used for determining the new plants from the pipeline.

        The pipeline forecast must be non-strictly increasing.

        Examples
        --------
        - [Forecast("name"), 0]

        Parameters
        ----------
        plant_name: str
            Name of plant for which pipeline is being assigned.
        existing_pipeline : NodeReference
            Forecast of existing pipelines.
        """

        command_assignment_to_dict(plant_name,
                                   existing_pipeline,
                                   self.existing_pipelines,
                                   scalar=False,
                                   type_=FORECAST,
                                   lower=0.)

    def set_allow_plant(self, plant_name, allow_plant):
        """
        Set a boolean flag for a given plant from the list of plants whether it is allowed or not.

        Examples
        --------
        - "plant_name", TRUE
        - "plant_name", FALSE

        Parameters
        ----------
        plant_name : str
            Name of plant in the list of plants.
        allow_plant : str
            Whether the plant is allowed or not.
        """

        command_assignment_to_boolean_dict(plant_name, allow_plant, self.allow_plant, allow_empty=True)

    def set_feed_constraint(self, feed_name, feed_constraint):
        """
        Set a static constraint for the amount of feed (feedstock or process) available in the region in tons/year.

        Examples
        --------
        - "feed_name", 1e6
        - "feed_name", Forecast("name")

        Parameters
        ----------
        feed_name : str
            The name of a feedstock or a process.
        feed_constraint : float | NodeReference
            The amount of feed available in tons/year.
        """

        command_assignment_to_dict(feed_name,
                                   feed_constraint,
                                   self.feed_constraints,
                                   type_=(FORECAST, VARIABLE),
                                   lower=0.)

    def set_export_distribution(self, port_name, export_distribution):
        """
        Set the fraction of fuel production that is exported to a given port.

        Examples
        --------
        - "port_name", 0.2
        - "port_name", Forecast("name")

        Parameters
        ----------
        port_name : str
            The name of a port.
        export_distribution : float | NodeReference
            The fraction of fuel production that is exported to the port.
        """

        command_assignment_to_dict(port_name,
                                   export_distribution,
                                   self.export_distribution,
                                   type_=(FORECAST, VARIABLE),
                                   lower=0.,
                                   upper=1.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if not self.assets:
            no_value_assigned_error(self, 'Plants')

        if self.fuel_demand_sensitivity is None:
            no_value_assigned_error(self, 'FuelDemandSensitivity')

        if self.fuel_cost_sensitivity is None:
            no_value_assigned_error(self, 'FuelCostSensitivity')

        if self.maximum_development is None:
            no_value_assigned_error(self, 'MaximumDevelopment')

        if self.inertia is None:
            self.inertia = Scalar(0)

        if self.maximum_ramp_up is None:
            self.maximum_ramp_up = Scalar(1)

        if self.minimum_offtake_duration is None:
            self.minimum_offtake_duration = Scalar(1)

        if self.jump_start_fraction is None:
            self.jump_start_fraction = 0.1

        if self._initial_capacity and (len(self.assets) != len(self._initial_capacity)):
            raise ValueError("{}: The length of Plants ({}) and InitialCapacity ({}) must correspond."
                             .format(self, len(self.assets), len(self._initial_capacity)))

        if self._initial_age_distribution and (len(self.assets) != len(self._initial_age_distribution)):
            raise ValueError("{}: The length of Plants ({}) and InitialAgeDistribution ({}) must correspond."
                             .format(self, len(self.assets), len(self._initial_age_distribution)))

        # check that pipelines satisfy various requirements
        if self.existing_pipelines:

            for pipeline in self.existing_pipelines.values():

                if pipeline is None:
                    continue

                # check that pipelines are cumulative
                if not is_non_strictly_increasing(pipeline.y):
                    raise ValueError("{}: Pipeline ({}) is not non-strictly increasing.".format(self, pipeline))

                # print a warning if the forecast allows extrapolation
                if pipeline.extrapolate == ExtrapolateID.LINEAR:
                    logger.warning("{}: Pipeline ({}) allows extrapolation and"
                                   " may therefore continue past the last date.".format(self, pipeline))

        # ensure consistent export distribution
        for port_name, export in self.export_distribution.items():
            if export is None:
                self.export_distribution[port_name] = Scalar(0.)

        for plant_name, allow in self.allow_plant.items():
            if allow is None:
                self.allow_plant[plant_name] = True

    def initialize_dependencies(self, feedstocks, ports, processes):
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        feedstocks : dict[str, Feedstock]
            All feedstocks in the simulation.
        ports : dict[str, Port]
            All ports in the simulation.
        processes : dict[str, Process]
            All processes in the simulation.
        """

        for feed_name in itertools.chain(feedstocks, processes):
            # stays None when unset: ProducerExpectation reads a missing constraint as unlimited
            self.feed_constraints.setdefault(feed_name, None)

        for port_name in ports:
            self.export_distribution.setdefault(port_name, None)

        for plant in self.assets:
            name = plant.name
            self.allow_plant.setdefault(name, None)
            # stays None when unset: a None entry means the plant has no committed pipeline
            self.existing_pipelines.setdefault(name, None)

    def initialize_expectation(self, length: int, feedstocks: dict[str, Feedstock],
                               fuels: dict[str, Fuel], ports: dict[str, Port],
                               processes: dict[str, Process]) -> None:

        plant_names = [plant.name for plant in self.assets]

        self.expectation = ProducerExpectation()
        self.expectation.initialize(length, plant_names, feedstocks, fuels, ports, processes)

    def initialize_profile(self, timeline: np.ndarray, feedstocks: dict[str, Feedstock],
                           fuels: dict[str, Fuel], processes: dict[str, Process]) -> None:

        self.profile = ProducerProfile()
        self.profile.initialize(timeline, feedstocks, fuels, processes)

    def calculate_expectation(self, timeline, idx):
        calculate_export_expectation(self, timeline, idx)

    def initialize_existing_producer(self, timeline):
        """
        Initialize the existing producer. This means discretizing the existing producer in time, by splitting the
        initial number of plants into individual increments with varying age.

        Parameters
        ----------
        timeline : np.ndarray
            Simulation timeline.
        """

        if self._initialized:
            return

        for plant in self.assets:
            plant.set_producer_assignment(self.name)

        idx = 0

        # existing producer
        self._define_initial_capacity()
        self._define_initial_age()
        self._initialize_decided()
        self._define_initial_multipliers()

        # clean up zero multipliers to reduce overhead
        # and avoid round-off error issue when calculating
        # increment average properties
        for a in range(len(self.increments)):
            self.increments[a] = [inc for inc in self.increments[a] if inc.multiplier > 0.]

        # existing pipeline
        define_existing_pipeline(self, timeline)

        # calculate the initial producer evolution expectation
        calculate_feed_availability(self, timeline, idx)
        calculate_evolution_expectation(self, timeline, idx)

        # store all possible production fuels for convenience
        for plant in self.assets:
            fuel = plant.fuel
            self.fuels.setdefault(fuel.name, fuel)

        # set static properties
        self._initialized = True

    def _define_initial_capacity(self):
        """
        Define the initial capacity of each plant type.
        """

        if not self._initial_capacity:

            # if the initial capacity is not
            # supplied by the user, then assume
            # zero initial capacity
            self._initial_capacity = [Scalar(0.) for _ in self.assets]

    # -- _AssetManager abstract interface -----------------------------------------------------------

    def _initialize_decided(self) -> None:
        """Set the decided field on each increment based on age + lead time."""
        for p, plant in enumerate(self.assets):
            lead_time = plant.lead_time.get()
            for inc in self.increments[p]:
                inc.decided = inc.age + lead_time

    def _get_initial_multiplier(self, index: int) -> float:
        capacity = self.assets[index].capacity.get()
        if capacity > 0.:
            return self._initial_capacity[index].get() / capacity
        logger.warning(
            "{}: Unable to initialize a capacity of tons/day from {} (plant {}) as the plant capacity is zero."
            .format(self, self._initial_capacity[index].get(), self.assets[index]))
        return 0.

    def perform_progression(self, timeline, idx):

        # decommission plants which are
        # past their technical lifetime
        perform_decommissioning(self)

        # deliver plants from the pipeline
        # which have passed their lead time
        perform_pipeline_delivery(self)

        # calculate the gap between feed used
        # in current and pipeline production
        # and the available supply
        calculate_feed_availability(self, timeline, idx)

    def perform_planning(self, timeline, time_step, idx):

        # add new plants to the pipeline
        # based on fuel supply/ demand gap
        perform_pipeline_planning(self, timeline, time_step, idx)

        # the feed gap needs to be updated
        # again prior to calculation the evolution
        # expectation to account newly added plants
        # to the pipeline
        calculate_feed_availability(self, timeline, idx)

        # calculate the expected evolution
        # of fuel supply for use to quantify
        # the next supply/demand gap
        calculate_evolution_expectation(self, timeline, idx)

    def update_increment_ages(self, time_step):
        """
        Update the ages of the increments with the progressed time since last time-step.
        This includes the plants awaiting delivery in the pipeline.

        Parameters
        ----------
        time_step : float
            Current time-step size.
        """

        dt = time_step / YEAR
        self._age_increments(self.increments, dt)
        self._age_increments(self.pipeline, dt)

    def can_produce(self, fuel_name):
        return fuel_name in self.fuels
