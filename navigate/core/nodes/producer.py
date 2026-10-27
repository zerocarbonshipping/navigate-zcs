# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Producer node, which builds and runs the plants of a fuel pathway."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_list,
    as_scalar,
    assign_boolean,
    assign_list,
    assign_reference_list,
    assign_value,
    check_forecast_is_cumulative,
    check_lengths_match,
    check_tables_are_finite,
    deck_attribute,
    deck_command,
    write_matching_keys,
)
from navigate.core.expectations import ProducerExpectation
from navigate.core.node import Node
from navigate.core.node_type import CURVE, FORECAST, PLANT, PRODUCER, VARIABLE
from navigate.core.results import ProducerResults

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.increment import PlantIncrement
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.forecast import Forecast
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.process import Process
    from navigate.core.results import ResultsContext
    from navigate.core.types_ import (
        CurveTableArgument,
        CurveTableInput,
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
    )
    from navigate.util.types_ import FloatArray


class Producer(Node):
    """A fuel producer: its buildable plants, pipeline, constraints and exports."""

    type = PRODUCER

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.plants: list[Plant]

        # plant uptake
        self.minimum_offtake_duration: ForecastInput = Scalar(1.0)
        self.fuel_demand_sensitivity: ForecastInput
        self.fuel_cost_sensitivity: ForecastInput
        self.inertia: ForecastInput = Scalar(0.0)

        # initial conditions
        self.initial_capacity: list[ScalarInput] = []
        self.initial_age_distribution: list[CurveTableInput] = []

        # constraints
        self.maximum_development: ForecastInput
        self.maximum_ramp_up: ForecastInput = Scalar(1.0)
        self.jump_start_fraction: ScalarInput = Scalar(0.1)

        # per plant, keyed by its name
        self.existing_pipelines: dict[str, Forecast | None] = {}
        self.allow_plant: dict[str, bool] = {}

        # per feed, keyed by the name of the feedstock or process
        self.feed_constraints: dict[str, ForecastInput | None] = {}

        # per port, keyed by its name
        self.export_distribution: dict[str, ForecastInput] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: ProducerExpectation = ProducerExpectation()
        self.results: ProducerResults = ProducerResults()

        # increments in service, and in the pipeline before their delivery
        self.increments: list[list[PlantIncrement]]
        self.pipeline: list[list[PlantIncrement]]

        # static variables
        self.fuels: dict[str, Fuel] = {}

        # dynamic variables
        self.current_uptake: FloatArray
        self.current_utilization: float

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_plants(self, plants: Plant | list[Plant]) -> None:
        """Set the list of plant types the producer can build."""
        self.plants = assign_reference_list(plants, PLANT, min_length=1, unique=True)

    @deck_attribute()
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

    @deck_attribute(required=True)
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

    @deck_attribute(required=True)
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

    @deck_attribute()
    def set_inertia(self, inertia: ForecastArgument) -> None:
        """Set the inertia used in the uptake decision of newbuild plants."""
        self.inertia = assign_value(
            as_scalar(inertia), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_initial_capacity(
        self, initial_capacity: ScalarArgument | list[ScalarArgument]
    ) -> None:
        """Set the initial capacity of each plant type."""
        entries: list[ScalarArgument] = as_list(initial_capacity)
        self.initial_capacity = assign_list(
            [as_scalar(entry) for entry in entries], type_=VARIABLE, lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_initial_age_distribution(
        self, initial_age_distribution: CurveTableArgument | list[CurveTableArgument]
    ) -> None:
        """Set the initial age distribution of each plant type."""
        entries: list[CurveTableArgument] = as_list(initial_age_distribution)
        self.initial_age_distribution = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=CURVE,
            lower=0.0,
            allow_expression=False,
        )

    @deck_attribute(required=True)
    def set_maximum_development(self, maximum_development: ForecastArgument) -> None:
        """Set the maximum number of plants that can be developed per year."""
        self.maximum_development = assign_value(
            as_scalar(maximum_development), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_maximum_ramp_up(self, maximum_ramp_up: ForecastArgument) -> None:
        """Set the maximum ramp-up of the development constraint's utilization."""
        self.maximum_ramp_up = assign_value(
            as_scalar(maximum_ramp_up), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute()
    def set_jump_start_fraction(self, jump_start_fraction: ScalarArgument) -> None:
        """Set the jump-start fraction of the supply/demand interaction."""
        self.jump_start_fraction = assign_value(
            as_scalar(jump_start_fraction), type_=VARIABLE, lower=0.0, upper=1.0
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command(SECTION_DEFINE)
    def set_existing_pipeline(self, plant_name: str, value: Forecast) -> None:
        """Set the existing pipeline of a plant."""
        write_matching_keys(
            plant_name,
            assign_value(
                value,
                allow_scalar=False,
                type_=FORECAST,
                lower=0.0,
                allow_expression=False,
            ),
            self.existing_pipelines,
        )

    @deck_command()
    def set_allow_plant(self, plant_name: str, value: str) -> None:
        """Set whether a plant may be built."""
        write_matching_keys(
            plant_name, assign_boolean(value), self.allow_plant, allow_empty=True
        )

    @deck_command()
    def set_feed_constraint(self, feed_name: str, value: ForecastArgument) -> None:
        """Set the constraint on a feed (feedstock or process) available."""
        write_matching_keys(
            feed_name,
            assign_value(
                as_scalar(value),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                allow_infinite=True,
            ),
            self.feed_constraints,
        )

    @deck_command()
    def set_export_distribution(self, port_name: str, value: ForecastArgument) -> None:
        """Set the weight with which the fuel production is exported to a port."""
        write_matching_keys(
            port_name,
            assign_value(
                as_scalar(value),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                upper=1.0,
            ),
            self.export_distribution,
        )

    # internal methods -----------------------------------------------------------------
    def apply_defaults(self) -> None:
        if not self.initial_capacity:
            self.initial_capacity = [Scalar(0.0) for _ in self.plants]

        if not self.initial_age_distribution:
            self.initial_age_distribution = [Scalar(0.0) for _ in self.plants]

    def check_consistency(self) -> None:
        plants = self.plants
        capacity = self.initial_capacity
        ages = self.initial_age_distribution
        existing = self.existing_pipelines.values()
        pipelines = [pipeline for pipeline in existing if pipeline is not None]

        check_lengths_match(self, "Plants", plants, "InitialCapacity", capacity)
        check_lengths_match(self, "Plants", plants, "InitialAgeDistribution", ages)
        check_tables_are_finite(self, "InitialAgeDistribution", ages)
        check_tables_are_finite(self, "Pipeline", pipelines)

        # a pipeline is the cumulative capacity committed to, in tons/day
        for pipeline in pipelines:
            check_forecast_is_cumulative(self, "Pipeline", pipeline)

    def initialize_dependencies(
        self,
        feedstocks: dict[str, Feedstock],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding in command calls.

        Parameters
        ----------
        feedstocks
            All feedstocks in the simulation.
        ports
            All ports in the simulation.
        processes
            All processes in the simulation.
        """
        # a None pipeline means the plant has no committed pipeline, and a None feed
        # constraint is read as unlimited
        for plant in self.plants:
            name = plant.name
            self.existing_pipelines.setdefault(name, None)
            self.allow_plant.setdefault(name, True)

        for feed_name in [*feedstocks, *processes]:
            self.feed_constraints.setdefault(feed_name, None)

        for port_name in ports:
            self.export_distribution.setdefault(port_name, Scalar(0.0))

    def initialize_expectation(
        self,
        length: int,
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        ports: dict[str, Port],
        processes: dict[str, Process],
    ) -> None:
        plant_names = [plant.name for plant in self.plants]
        self.expectation.initialize(
            length, plant_names, feedstocks, fuels, ports, processes
        )

    def initialize_results(
        self,
        context: ResultsContext,
        feedstock_names: Sequence[str],
        process_names: Sequence[str],
    ) -> None:
        self.results.initialize(context, feedstock_names, process_names)

    def can_produce(self, fuel_name: str) -> bool:
        return fuel_name in self.fuels
