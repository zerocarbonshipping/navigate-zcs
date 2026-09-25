# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Producer node, which builds and runs the plants of a fuel pathway."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
)
from navigate.core.enum_ import ExtrapolateID
from navigate.core.expectations import ProducerExpectation
from navigate.core.node_type import FORECAST, PLANT, PRODUCER, VARIABLE
from navigate.core.nodes._asset_manager import _AssetManager
from navigate.core.profiles import ProducerProfile
from navigate.exceptions import no_value_assigned_error
from navigate.util import is_non_strictly_increasing

if TYPE_CHECKING:
    from navigate.core.expression import Expression
    from navigate.core.increment import Increment
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.forecast import Forecast
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.input_kinds import ForecastInput, NumberInput, ScalarInput
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process
    from navigate.util import FloatArray

logger = logging.getLogger(__name__)


class Producer(_AssetManager):
    """A fuel producer: its buildable plants, pipeline, constraints and exports."""

    def __init__(self, name: str) -> None:
        super().__init__(name, PRODUCER)

        # external variables -----------------------------------------------------------
        # plant uptake
        self.minimum_offtake_duration: ForecastInput = Scalar(1.0)
        self.fuel_demand_sensitivity: ForecastInput
        self.fuel_cost_sensitivity: ForecastInput

        # initial conditions
        self._initial_capacity: list[ScalarInput] = []

        # existing pipeline
        self.existing_pipelines: dict[str, Forecast | Expression | None] = {}

        # constraints
        self.maximum_development: ForecastInput
        self.feed_constraints: dict[str, ForecastInput | None] = {}
        self.jump_start_fraction: NumberInput = 0.1
        self.maximum_ramp_up: ForecastInput = Scalar(1.0)

        # export
        self.export_distribution: dict[str, ForecastInput] = {}

        # boolean
        self.allow_plant: dict[str, bool] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: ProducerExpectation = ProducerExpectation()
        self.profile: ProducerProfile = ProducerProfile()

        # pipeline increments (Producer-specific, separate from active increments in
        # _AssetManager)
        self.pipeline: list[list[Increment]] = []
        self._increment_stores.append(self.pipeline)

        # static variables
        self.fuels: dict[str, Fuel] = {}

        # dynamic variables
        self.current_utilization: float | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_plants(self, plants: list[Plant]) -> None:
        """
        Set the list of plant types that can be built.

        Examples
        --------
        - Plant("name")
        - [Plant("name1"), Plant("name2")]

        Parameters
        ----------
        plants
            The list of plants that can be built.
        """
        self.assets = assign_list(
            as_list(plants), unique=True, scalar=False, type_=PLANT
        )

    def set_minimum_offtake_duration(
        self, minimum_offtake_duration: float | ForecastInput
    ) -> None:
        """
        Set the minimum offtake duration required for building new plants.

        Examples
        --------
        - 7
        - Forecast("name")

        Parameters
        ----------
        minimum_offtake_duration
            The minimum offtake agreement for building new plants.
        """
        self.minimum_offtake_duration = assign_value(
            as_scalar(minimum_offtake_duration), type_=(FORECAST, VARIABLE), lower=1.0
        )

    def set_fuel_demand_sensitivity(
        self, fuel_demand_sensitivity: float | ForecastInput
    ) -> None:
        """
        Set the sensitivity of the fuel-pathway choice to expected demand.

        The value is an odds ratio: a pathway whose expected demand is 10% higher
        receives this many times the odds of an otherwise identical pathway. For example
        1.25 means a 10% higher demand gives 1.25 times the odds, and 1 means no
        preference. Demand is higher-is-better, so use a value above 1.

        Examples
        --------
        - 1.25
        - Forecast("name")

        Parameters
        ----------
        fuel_demand_sensitivity
            Odds ratio for a 10% higher expected demand in the between-pathway choice.
        """
        self.fuel_demand_sensitivity = assign_value(
            as_scalar(fuel_demand_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_fuel_cost_sensitivity(
        self, fuel_cost_sensitivity: float | ForecastInput
    ) -> None:
        """
        Set the sensitivity of the plant choice to levelized cost of fuel (LCoF).

        The value is an odds ratio: a plant whose LCoF is 10% higher receives this many
        times the odds of an otherwise identical plant. For example 0.5 means a 10%
        higher LCoF halves the odds, and 1 means no preference. LCoF is lower-is-better,
        so use a value below 1.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        fuel_cost_sensitivity
            Odds ratio for a 10% higher LCoF in the within-pathway plant choice.
        """
        self.fuel_cost_sensitivity = assign_value(
            as_scalar(fuel_cost_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_initial_capacity(self, initial_capacity: list[float | ScalarInput]) -> None:
        """
        Set the list of initial capacity for each plant type in tons/day.

        The list must have the same length as the list of plants.

        Examples
        --------
        - [500, 0]

        Parameters
        ----------
        initial_capacity
            List of initial production in tons/day.
        """
        entries: list[float | ScalarInput] = as_list(initial_capacity)
        self._initial_capacity = assign_list(
            [as_scalar(entry) for entry in entries], type_=VARIABLE, lower=0.0
        )

    def set_maximum_development(
        self, maximum_development: float | ForecastInput
    ) -> None:
        """
        Set the maximum number of plants that can be developed per year.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        maximum_development
            Maximum developments of plants per year.
        """
        self.maximum_development = assign_value(
            as_scalar(maximum_development), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_maximum_ramp_up(self, maximum_ramp_up: float | ForecastInput) -> None:
        """
        Set the maximum ramp-up of the development constraint's utilization per year.

        Examples
        --------
        - 0.2
        - Forecast("name")

        Parameters
        ----------
        maximum_ramp_up
            The maximum ramp-up for the utilization of the development constraint.
        """
        self.maximum_ramp_up = assign_value(
            as_scalar(maximum_ramp_up), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    def set_jump_start_fraction(self, jump_start_fraction: NumberInput) -> None:
        """
        Set the jump-start fraction for supply/demand interaction absent production.

        Due to the use of self.current_uptake and self.current_utilization in the
        expectation calculations it is necessary to include a "jump-start" fraction in
        case those values are zero, to get the supply/demand interaction started.

        Examples
        --------
        - 0.1

        Parameters
        ----------
        jump_start_fraction
            The jump-start fraction for supply/demand interaction.
        """
        self.jump_start_fraction = assign_value(
            jump_start_fraction, lower=0.0, upper=1.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_existing_pipeline(
        self, plant_name: str, existing_pipeline: Forecast | Expression
    ) -> None:
        """
        Set an existing pipeline for a plant, used to determine new plants from it.

        The pipeline forecast must be non-strictly increasing.

        Examples
        --------
        - "plant_name", Forecast("name")

        Parameters
        ----------
        plant_name
            Name of plant for which pipeline is being assigned.
        existing_pipeline
            Forecast of existing pipelines.
        """
        command_assignment_to_dict(
            plant_name,
            as_scalar(existing_pipeline),
            self.existing_pipelines,
            scalar=False,
            type_=FORECAST,
            lower=0.0,
        )

    def set_allow_plant(self, plant_name: str, allow_plant: str) -> None:
        """
        Set a boolean flag for whether a given plant is allowed to be built.

        Examples
        --------
        - "plant_name", TRUE
        - "plant_name", FALSE

        Parameters
        ----------
        plant_name
            Name of plant in the list of plants.
        allow_plant
            Whether the plant is allowed or not.
        """
        command_assignment_to_boolean_dict(
            plant_name, allow_plant, self.allow_plant, allow_empty=True
        )

    def set_feed_constraint(
        self, feed_name: str, feed_constraint: float | ForecastInput
    ) -> None:
        """
        Set a static feed (feedstock or process) constraint for the region, tons/year.

        Examples
        --------
        - "feed_name", 1e6
        - "feed_name", Forecast("name")

        Parameters
        ----------
        feed_name
            The name of a feedstock or a process.
        feed_constraint
            The amount of feed available in tons/year.
        """
        command_assignment_to_dict(
            feed_name,
            as_scalar(feed_constraint),
            self.feed_constraints,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_export_distribution(
        self, port_name: str, export_distribution: float | ForecastInput
    ) -> None:
        """
        Set the weight with which the fuel production is exported to a port.

        The weights of all ports are normalized to sum to one in every time-step,
        so a weight is a share of the production only when the weights assigned
        across the ports already sum to one. If no port carries a positive weight,
        the production is split equally across all ports.

        Examples
        --------
        - "port_name", 0.2
        - "port_name", Forecast("name")

        Parameters
        ----------
        port_name
            The name of a port.
        export_distribution
            The relative weight of the port in the export of the fuel production.
        """
        command_assignment_to_dict(
            port_name,
            as_scalar(export_distribution),
            self.export_distribution,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.assets:
            no_value_assigned_error(self, "Plants")

    def check_consistency(self) -> None:

        if self._initial_capacity and (len(self.assets) != len(self._initial_capacity)):
            raise ValueError(
                f"{self}: The length of Plants ({len(self.assets)}) and InitialCapacity"
                f" ({len(self._initial_capacity)}) must correspond."
            )

        if self._initial_age_distribution and (
            len(self.assets) != len(self._initial_age_distribution)
        ):
            raise ValueError(
                f"{self}: The length of Plants ({len(self.assets)}) and"
                f" InitialAgeDistribution"
                f" ({len(self._initial_age_distribution)}) must correspond."
            )

        for pipeline in self.existing_pipelines.values():
            if pipeline is None:
                continue

            # a pipeline is a cumulative count of the plants committed to
            if not is_non_strictly_increasing(pipeline.y):
                raise ValueError(
                    f"{self}: Pipeline ({pipeline}) is not non-strictly increasing."
                )

            if pipeline.extrapolate == ExtrapolateID.LINEAR:
                logger.warning(
                    "%s: Pipeline (%s) allows extrapolation and may therefore "
                    "continue past the last date.",
                    self,
                    pipeline,
                )

    def initialize_dependencies(
        self,
        feedstocks: dict[str, Feedstock],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        feedstocks
            All feedstocks in the simulation.
        ports
            All ports in the simulation.
        processes
            All processes in the simulation.
        """
        for feed_name in itertools.chain(feedstocks, processes):
            # stays None when unset: ProducerExpectation reads a missing constraint as
            # unlimited
            self.feed_constraints.setdefault(feed_name, None)

        for port_name in ports:
            self.export_distribution.setdefault(port_name, Scalar(0.0))

        for plant in self.assets:
            name = plant.name
            self.allow_plant.setdefault(name, True)
            # stays None when unset: a None entry means the plant has no committed
            # pipeline
            self.existing_pipelines.setdefault(name, None)

    def initialize_expectation(
        self,
        length: int,
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:

        plant_names = [plant.name for plant in self.assets]

        self.expectation.initialize(
            length, plant_names, feedstocks, fuels, ports, processes
        )

    def initialize_profile(
        self,
        timeline: FloatArray,
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        processes: dict[str, Process],
    ) -> None:

        self.profile.initialize(timeline, feedstocks, fuels, processes)

    def define_initial_capacity(self) -> None:
        """Define the initial capacity of each plant type."""
        if not self._initial_capacity:
            # if the initial capacity is not
            # supplied by the user, then assume
            # zero initial capacity
            self._initial_capacity = [Scalar(0.0) for _ in self.assets]

    def define_initial_decided(self) -> None:
        """Set the decided field on each increment based on age + lead time."""
        for p, plant in enumerate(self.assets):
            lead_time = plant.lead_time.get()
            for inc in self.increments[p]:
                inc.decided = inc.age + lead_time

    # _AssetManager abstract interface

    def _get_initial_multiplier(self, index: int) -> float:
        plant = self.plants[index]
        capacity = plant.capacity.get()
        if capacity > 0.0:
            return self._initial_capacity[index].get() / capacity
        logger.warning(
            "%s: Unable to initialize a capacity of tons/day from %s (plant %s) as the "
            "plant capacity is zero.",
            self,
            self._initial_capacity[index].get(),
            plant,
        )
        return 0.0

    def can_produce(self, fuel_name: str) -> bool:
        return fuel_name in self.fuels

    # public domain name for the inherited assets list
    @property
    def plants(self) -> list[Plant]:
        return self.assets
