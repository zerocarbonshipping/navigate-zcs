# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Producer node, which builds and runs the plants of a fuel pathway."""

from __future__ import annotations

import itertools
import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    Scalar,
    as_list,
    as_scalar,
    assign_list,
    assign_reference_list,
    assign_value,
    command_assignment_to_boolean_dict,
    write_matching_keys,
)
from navigate.core.enum_ import ExtrapolateID
from navigate.core.expectations import ProducerExpectation
from navigate.core.increment import PlantIncrement
from navigate.core.node_type import FORECAST, PLANT, PRODUCER, VARIABLE
from navigate.core.nodes._asset_manager import _AssetManager
from navigate.core.nodes.plant import Plant
from navigate.core.profiles import ProducerProfile
from navigate.exceptions import UnassignedAttributeError
from navigate.util import is_non_strictly_increasing

if TYPE_CHECKING:
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.forecast import Forecast
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
    )
    from navigate.util import FloatArray

logger = logging.getLogger(__name__)


class Producer(_AssetManager[Plant, PlantIncrement]):
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
        self.existing_pipelines: dict[str, Forecast | None] = {}

        # constraints
        self.maximum_development: ForecastInput
        self.feed_constraints: dict[str, ForecastInput | None] = {}
        self.jump_start_fraction: ScalarInput = Scalar(0.1)
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
        self.pipeline: list[list[PlantIncrement]] = []
        self._increment_stores.append(self.pipeline)

        # static variables
        self.fuels: dict[str, Fuel] = {}

        # dynamic variables
        self.current_utilization: float = 0.0

    # external methods (DSL attributes) ------------------------------------------------
    def set_plants(self, plants: Plant | list[Plant]) -> None:
        """Set the list of plant types the producer can build."""
        self.assets = assign_reference_list(plants, PLANT, unique=True)

    def set_minimum_offtake_duration(
        self, minimum_offtake_duration: ForecastArgument
    ) -> None:
        """Set the minimum offtake duration required for building new plants."""
        self.minimum_offtake_duration = assign_value(
            as_scalar(minimum_offtake_duration),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_fuel_demand_sensitivity(
        self, fuel_demand_sensitivity: ForecastArgument
    ) -> None:
        """Set the sensitivity of the fuel-pathway choice to expected demand."""
        self.fuel_demand_sensitivity = assign_value(
            as_scalar(fuel_demand_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_fuel_cost_sensitivity(
        self, fuel_cost_sensitivity: ForecastArgument
    ) -> None:
        """Set the sensitivity of the plant choice to levelized cost of fuel."""
        self.fuel_cost_sensitivity = assign_value(
            as_scalar(fuel_cost_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    def set_initial_capacity(
        self, initial_capacity: ScalarArgument | list[ScalarArgument]
    ) -> None:
        """Set the initial capacity of each plant type."""
        entries: list[ScalarArgument] = as_list(initial_capacity)
        self._initial_capacity = assign_list(
            [as_scalar(entry) for entry in entries], type_=VARIABLE, lower=0.0
        )

    def set_maximum_development(self, maximum_development: ForecastArgument) -> None:
        """Set the maximum number of plants that can be developed per year."""
        self.maximum_development = assign_value(
            as_scalar(maximum_development), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_maximum_ramp_up(self, maximum_ramp_up: ForecastArgument) -> None:
        """Set the maximum ramp-up of the development constraint's utilization."""
        self.maximum_ramp_up = assign_value(
            as_scalar(maximum_ramp_up), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    def set_jump_start_fraction(self, jump_start_fraction: ScalarArgument) -> None:
        """Set the jump-start fraction of the supply/demand interaction."""
        self.jump_start_fraction = assign_value(
            as_scalar(jump_start_fraction), type_=VARIABLE, lower=0.0, upper=1.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_existing_pipeline(
        self, plant_name: str, existing_pipeline: Forecast
    ) -> None:
        """Set the existing pipeline of a plant."""
        write_matching_keys(
            plant_name,
            assign_value(
                existing_pipeline,
                allow_scalar=False,
                type_=FORECAST,
                lower=0.0,
                allow_expression=False,
            ),
            self.existing_pipelines,
        )

    def set_allow_plant(self, plant_name: str, allow_plant: str) -> None:
        """Set whether a plant may be built."""
        command_assignment_to_boolean_dict(
            plant_name, allow_plant, self.allow_plant, allow_empty=True
        )

    def set_feed_constraint(
        self, feed_name: str, feed_constraint: ForecastArgument
    ) -> None:
        """Set the constraint on a feed (feedstock or process) available."""
        write_matching_keys(
            feed_name,
            assign_value(
                as_scalar(feed_constraint),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                allow_infinite=True,
            ),
            self.feed_constraints,
        )

    def set_export_distribution(
        self, port_name: str, export_distribution: ForecastArgument
    ) -> None:
        """Set the weight with which the fuel production is exported to a port."""
        write_matching_keys(
            port_name,
            assign_value(
                as_scalar(export_distribution),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                upper=1.0,
            ),
            self.export_distribution,
        )

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.assets:
            raise UnassignedAttributeError(str(self), "Plants")

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

        self._check_initial_age_distribution_is_finite()

        for pipeline in self.existing_pipelines.values():
            if pipeline is None:
                continue

            # the pipeline is read as a table, never evaluated, so no bound it
            # is assigned under ever checks its entries
            if not np.all(np.isfinite(pipeline.y)):
                raise ValueError(
                    f"{self}: Pipeline ({pipeline}) must hold finite values."
                )

            # a pipeline is the cumulative capacity committed to, in tons/day
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

    def _new_increment(self, age: float, age_span: float) -> PlantIncrement:
        # define_initial_decided sets the decided time before anything reads it
        return PlantIncrement(multiplier=0.0, age=age, age_span=age_span, decided=0.0)

    def _age_increments(
        self, increment_lists: list[list[PlantIncrement]], dt: float
    ) -> None:
        # the time since decision dates the plant attributes a cohort was decided with
        for incs in increment_lists:
            for inc in incs:
                inc.age += dt
                inc.decided += dt

    def can_produce(self, fuel_name: str) -> bool:
        return fuel_name in self.fuels

    # public domain name for the inherited assets list
    @property
    def plants(self) -> list[Plant]:
        return self.assets
