# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Fleet node, a vessel segment and the decisions made for it."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_list,
    as_scalar,
    assign_boolean,
    assign_fraction_list,
    assign_id,
    assign_list,
    assign_member,
    assign_reference_list,
    assign_value,
    check_curves_are_finite,
    deck_attribute,
    deck_command,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.enum_ import (
    PORT_ENERGY_DEMANDS,
    EnergyDemandID,
    ExtrapolateID,
    SpeedAlignmentID,
)
from navigate.core.expectations import FleetExpectation
from navigate.core.node import Node
from navigate.core.node_type import CURVE, FLEET, FORECAST, TECHNOLOGY, VARIABLE, VESSEL
from navigate.core.nodes.forecast import Forecast
from navigate.core.results import FleetResults
from navigate.core.technology_package import PackageCostFlows, TechnologyPackage
from navigate.exceptions import UnassignedAttributeError
from navigate.util import is_nondecreasing

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.expression import Expression
    from navigate.core.increment import VesselIncrement
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.results.results_context import ResultsContext
    from navigate.core.types_ import (
        CurveTableArgument,
        CurveTableInput,
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
    )
    from navigate.util.types_ import FloatArray

logger = logging.getLogger(__name__)


class Fleet(Node):
    """A segment of vessel types with its newbuild, scrap and retrofit decisions."""

    type = FLEET

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.vessels: list[Vessel]
        self.trade_growth: ForecastInput = Scalar(0.0)
        self.fixed_scrap_rate: ForecastInput | None = None
        self.allow_secondary_scrapping: bool = True
        self.intra_fuel_sensitivity: ForecastInput
        self.inter_fuel_sensitivity: ForecastInput
        self.fuel_conversion_sensitivity: ForecastInput = Scalar(2.0)
        self.memory: ForecastInput = Scalar(0.5)
        self.inertia: ForecastInput = Scalar(0.0)
        self.initial_vessels: ScalarInput
        self.allow_speed_management: bool = False
        self.maximum_speed_change: ForecastInput = Scalar(np.inf)
        self.speed_alignment: SpeedAlignmentID = SpeedAlignmentID.INDIVIDUAL
        self.assume_reference_speed_optimal: bool = False
        self.retrofit_frequency: ForecastInput = Scalar(5.0)
        self.technology_sensitivity: ForecastInput | None = None
        self.technology_cost_of_capital: ForecastInput | None = None
        self.technology_horizon: ForecastInput = Scalar(3.0)
        self.speed_horizon: ForecastInput = Scalar(1.0)
        self.fuel_conversion_minimum_age: ForecastInput = Scalar(0.0)
        self.allow_technology_approximation: bool = True
        self.initial_split: list[float] = []
        self.initial_age_distribution: list[CurveTableInput] = []
        self.initial_technology_share: dict[
            tuple[str, str], Curve | Expression | None
        ] = {}
        self.orderbooks: list[ForecastInput] = []
        self.technologies: list[Technology] = []
        self.operational_saving_sea: dict[EnergyDemandID, ForecastInput] = {
            demand: Scalar(0.0) for demand in EnergyDemandID
        }
        self.operational_saving_port: dict[EnergyDemandID, ForecastInput] = {
            demand: Scalar(0.0) for demand in PORT_ENERGY_DEMANDS
        }
        self.fuel_conversion_cost: dict[tuple[str, str], ForecastInput | None] = {}
        self.fuel_conversion_limit: dict[tuple[str, str], ForecastInput] = {}
        self.newbuild_limit: dict[str, ForecastInput] = {}
        self.newbuild_technology_limit: dict[str, ForecastInput] = {}
        self.retrofit_technology_limit: dict[str, ForecastInput] = {}
        self.allow_vessel: dict[str, bool] = {}
        self.newbuild_available: dict[str, bool] = {}
        self.conversion_available: dict[str, bool] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: FleetExpectation = FleetExpectation()
        self.results: FleetResults = FleetResults()

        self.increments: list[list[VesselIncrement]]
        self.current_uptake: FloatArray
        self.fuel_conversion_expenses: FloatArray
        self.trade: FloatArray
        self.newbuild_package_uptake: list[FloatArray]
        self.orders_delivered: FloatArray
        self.orders_postponed: FloatArray
        self.technology_packages: list[TechnologyPackage]
        self.package_cost_flows: PackageCostFlows = PackageCostFlows()

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_vessels(self, vessels: Vessel | list[Vessel]) -> None:
        """Set the vessel types that exist for the fleet."""
        self.vessels = assign_reference_list(vessels, VESSEL, min_length=1, unique=True)

    @deck_attribute()
    def set_memory(self, memory: ForecastArgument) -> None:
        """Set the memory's exponential decay used in the newbuild uptake decision."""
        self.memory = assign_value(
            as_scalar(memory), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute()
    def set_inertia(self, inertia: ForecastArgument) -> None:
        """Set the inertia used in the uptake decision of newbuild vessels."""
        self.inertia = assign_value(
            as_scalar(inertia), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute()
    def set_fixed_scrap_rate(self, fixed_scrap_rate: ForecastArgument) -> None:
        """Set the fixed scrap rate of the fleet."""
        self.fixed_scrap_rate = assign_value(
            as_scalar(fixed_scrap_rate),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
        )

    @deck_attribute()
    def set_allow_secondary_scrapping(self, allow_secondary_scrapping: str) -> None:
        """Set whether secondary scrapping is allowed."""
        self.allow_secondary_scrapping = assign_boolean(allow_secondary_scrapping)

    @deck_attribute(SECTION_DEFINE)
    def set_trade_growth(self, trade_growth: ForecastArgument) -> None:
        """Set the trade growth of the fleet."""
        self.trade_growth = assign_value(
            as_scalar(trade_growth), type_=(FORECAST, VARIABLE)
        )

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_initial_vessels(self, initial_vessels: ScalarArgument) -> None:
        """Set the initial number of vessels in the fleet."""
        self.initial_vessels = assign_value(
            as_scalar(initial_vessels), type_=VARIABLE, lower=0, inclusive_lower=False
        )

    @deck_attribute(SECTION_DEFINE)
    def set_initial_split(self, initial_split: list[float]) -> None:
        """Set the initial distribution of vessel types in the fleet."""
        self.initial_split, rescaled = assign_fraction_list(initial_split)

        if rescaled:
            logger.warning(
                "%s: 'InitialSplit' is rescaled proportionally to sum to 1.", self
            )

    @deck_attribute(SECTION_DEFINE)
    def set_initial_age_distribution(
        self, initial_age_distribution: CurveTableArgument | list[CurveTableArgument]
    ) -> None:
        """Set the initial age distribution of each vessel type."""
        entries: list[CurveTableArgument] = as_list(initial_age_distribution)
        self.initial_age_distribution = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=CURVE,
            lower=0.0,
            allow_expression=False,
        )

    @deck_attribute(SECTION_DEFINE)
    def set_technologies(self, technologies: Technology | list[Technology]) -> None:
        """Set the technologies that can be installed on the fleet's vessels."""
        self.technologies = assign_reference_list(technologies, TECHNOLOGY, unique=True)

    @deck_attribute(required=True)
    def set_intra_fuel_sensitivity(
        self, intra_fuel_sensitivity: ForecastArgument
    ) -> None:
        """Set the within-fuel technology choice's sensitivity to LCOT."""
        self.intra_fuel_sensitivity = assign_value(
            as_scalar(intra_fuel_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute(required=True)
    def set_inter_fuel_sensitivity(
        self, inter_fuel_sensitivity: ForecastArgument
    ) -> None:
        """Set the fuel-type choice's sensitivity to LCOT."""
        self.inter_fuel_sensitivity = assign_value(
            as_scalar(inter_fuel_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute()
    def set_technology_sensitivity(
        self, technology_sensitivity: ForecastArgument
    ) -> None:
        """Set the technology package choice's sensitivity to its NPV."""
        self.technology_sensitivity = assign_value(
            as_scalar(technology_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute()
    def set_technology_cost_of_capital(
        self, technology_cost_of_capital: ForecastArgument
    ) -> None:
        """Set the cost of capital used for evaluating technology investments."""
        self.technology_cost_of_capital = assign_value(
            as_scalar(technology_cost_of_capital),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    @deck_attribute()
    def set_technology_horizon(self, technology_horizon: ForecastArgument) -> None:
        """Set the smoothing horizon of the technology energy-scarcity belief."""
        self.technology_horizon = assign_value(
            as_scalar(technology_horizon), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_speed_horizon(self, speed_horizon: ForecastArgument) -> None:
        """Set the smoothing horizon of the speed energy-scarcity belief."""
        self.speed_horizon = assign_value(
            as_scalar(speed_horizon), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_retrofit_frequency(self, retrofit_frequency: ForecastArgument) -> None:
        """Set how often a vessel can retrofit technology or convert fuel."""
        self.retrofit_frequency = assign_value(
            as_scalar(retrofit_frequency),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute(SECTION_DEFINE)
    def set_orderbooks(
        self, orderbooks: ForecastArgument | list[ForecastArgument]
    ) -> None:
        """Set the orderbook of each vessel type."""
        entries: list[ForecastArgument] = as_list(orderbooks)
        self.orderbooks = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    @deck_attribute()
    def set_allow_speed_management(self, allow_speed_management: str) -> None:
        """Set whether speed management is allowed."""
        self.allow_speed_management = assign_boolean(allow_speed_management)

    @deck_attribute()
    def set_maximum_speed_change(self, maximum_speed_change: ForecastArgument) -> None:
        """Set the maximum yearly speed change under speed management."""
        self.maximum_speed_change = assign_value(
            as_scalar(maximum_speed_change),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            allow_infinite=True,
        )

    @deck_attribute()
    def set_speed_alignment(self, speed_alignment: str) -> None:
        """Set the method used to align speed across vessel types."""
        self.speed_alignment = assign_id(speed_alignment, SpeedAlignmentID)

    @deck_attribute()
    def set_assume_reference_speed_optimal(
        self, assume_reference_speed_optimal: str
    ) -> None:
        """Set whether the reference speed is taken as the market optimum."""
        self.assume_reference_speed_optimal = assign_boolean(
            assume_reference_speed_optimal
        )

    @deck_attribute()
    def set_fuel_conversion_sensitivity(
        self, fuel_conversion_sensitivity: ForecastArgument
    ) -> None:
        """Set the fuel-conversion choice's sensitivity to its NPV."""
        self.fuel_conversion_sensitivity = assign_value(
            as_scalar(fuel_conversion_sensitivity),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute()
    def set_fuel_conversion_minimum_age(
        self, fuel_conversion_minimum_age: ForecastArgument
    ) -> None:
        """Set the minimum age at which a vessel can convert fuel."""
        self.fuel_conversion_minimum_age = assign_value(
            as_scalar(fuel_conversion_minimum_age),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    @deck_attribute()
    def set_allow_technology_approximation(
        self, allow_technology_approximation: str
    ) -> None:
        """Set whether technology uptake is approximated from other fleets."""
        self.allow_technology_approximation = assign_boolean(
            allow_technology_approximation
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_fuel_conversion_cost(
        self, vessel_name_from: str, vessel_name_to: str, value: ForecastArgument
    ) -> None:
        """Set the cost of converting a vessel type to another."""
        write_matching_key_pairs(
            (vessel_name_from, vessel_name_to),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.fuel_conversion_cost,
        )

    @deck_command()
    def set_fuel_conversion_limit(
        self, vessel_name_from: str, vessel_name_to: str, value: ForecastArgument
    ) -> None:
        """Set the yearly cap on fuel conversions between two vessel types."""
        write_matching_key_pairs(
            (vessel_name_from, vessel_name_to),
            assign_value(
                as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
            ),
            self.fuel_conversion_limit,
        )

    @deck_command()
    def set_allow_vessel(self, vessel_name: str, value: str) -> None:
        """Set whether a vessel type may enter the fleet."""
        write_matching_keys(
            vessel_name, assign_boolean(value), self.allow_vessel, allow_empty=True
        )

    @deck_command()
    def set_newbuild_available(self, vessel_name: str, value: str) -> None:
        """Set whether a vessel type is available as a newbuild."""
        write_matching_keys(
            vessel_name,
            assign_boolean(value),
            self.newbuild_available,
            allow_empty=True,
        )

    @deck_command()
    def set_conversion_available(self, vessel_name: str, value: str) -> None:
        """Set whether a vessel type is available as a conversion target."""
        write_matching_keys(
            vessel_name,
            assign_boolean(value),
            self.conversion_available,
            allow_empty=True,
        )

    @deck_command(SECTION_DEFINE)
    def set_initial_technology_share(
        self, vessel_name: str, technology_name: str, value: Curve | Expression
    ) -> None:
        """Set the initial technology uptake by vessel age."""
        write_matching_key_pairs(
            (vessel_name, technology_name),
            assign_value(value, allow_scalar=False, type_=CURVE, lower=0.0, upper=1.0),
            self.initial_technology_share,
        )

    @deck_command()
    def set_newbuild_limit(self, vessel_name: str, value: ForecastArgument) -> None:
        """Set the yearly newbuild cap of a vessel type."""
        write_matching_keys(
            vessel_name,
            assign_value(
                as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
            ),
            self.newbuild_limit,
        )

    @deck_command()
    def set_newbuild_technology_limit(
        self, technology_name: str, value: ForecastArgument
    ) -> None:
        """Set the yearly cap on newbuild installs of a technology."""
        write_matching_keys(
            technology_name,
            assign_value(
                as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
            ),
            self.newbuild_technology_limit,
        )

    @deck_command()
    def set_retrofit_technology_limit(
        self, technology_name: str, value: ForecastArgument
    ) -> None:
        """Set the yearly cap on retrofits of a technology."""
        write_matching_keys(
            technology_name,
            assign_value(
                as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
            ),
            self.retrofit_technology_limit,
        )

    @deck_command()
    def set_operational_saving_sea(
        self, energy_type: str, value: ForecastArgument
    ) -> None:
        """Set the energy fraction saved at sea through operational measures."""
        id_ = assign_id(energy_type, EnergyDemandID)
        value_ = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

        write_matching_keys(id_, value_, self.operational_saving_sea)

    @deck_command()
    def set_operational_saving_port(
        self, energy_type: str, value: ForecastArgument
    ) -> None:
        """Set the energy fraction saved in port through operational measures."""
        id_ = assign_member(energy_type, PORT_ENERGY_DEMANDS)
        value_ = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

        write_matching_keys(id_, value_, self.operational_saving_port)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        if self.technologies and self.technology_sensitivity is None:
            raise UnassignedAttributeError(str(self), "TechnologySensitivity")

    def apply_defaults(self) -> None:
        # without a supplied initial split, the cargo-miles are split uniformly
        if not self.initial_split:
            self.initial_split = [1.0 / len(self.vessels) for _ in self.vessels]

        if not self.initial_age_distribution:
            self.initial_age_distribution = [Scalar(0.0) for _ in self.vessels]

    def apply_command_defaults(self) -> None:
        # cross-pair keys exist only after commands fill fuel_conversion_cost, so
        # their limits are seeded here rather than in initialize_dependencies
        for key, cost in self.fuel_conversion_cost.items():
            if cost is not None:
                self.fuel_conversion_limit.setdefault(key, Scalar(1.0))

    def check_consistency(self) -> None:
        if len(self.vessels) != len(self.initial_split):
            raise ValueError(
                f"{self}: The length of Vessel ({len(self.vessels)}) and "
                f"InitialSplit ({len(self.initial_split)}) must correspond."
            )

        if len(self.vessels) != len(self.initial_age_distribution):
            raise ValueError(
                f"{self}: The length of Vessel ({len(self.vessels)}) and "
                f"InitialAgeDistribution ({len(self.initial_age_distribution)}) "
                "must correspond."
            )

        distributions = self.initial_age_distribution
        check_curves_are_finite(self, "InitialAgeDistribution", distributions)

        if not self.orderbooks:
            return

        if len(self.vessels) != len(self.orderbooks):
            raise ValueError(
                f"{self}: The length of Vessel ({len(self.vessels)}) and "
                f"Orderbooks ({len(self.orderbooks)}) must correspond."
            )

        for orderbook in self.orderbooks:
            if not isinstance(orderbook, Forecast):
                continue

            # an orderbook is a cumulative count of the vessels on order
            if not is_nondecreasing(orderbook.y):
                raise ValueError(
                    f"{self}: Orderbook ({orderbook}) is not non-strictly increasing."
                )

            if orderbook.extrapolate == ExtrapolateID.LINEAR:
                logger.warning(
                    "%s: Orderbook (%s) allows extrapolation and may therefore "
                    "continue past the last date.",
                    self,
                    orderbook,
                )

    def initialize_dependencies(self) -> None:
        """Initialize dependent dictionaries so command calls can use wildcards."""
        # a None conversion cost marks a pair as not convertible and a None share
        # means no initial share; the self-pair limit exists only so
        # write_matching_key_pairs can validate cross-pair keys
        for vessel in self.vessels:
            name = vessel.name
            self.fuel_conversion_cost.setdefault((name, name), None)
            self.fuel_conversion_limit.setdefault((name, name), Scalar(1.0))
            self.newbuild_limit.setdefault(name, Scalar(1.0))
            self.allow_vessel.setdefault(name, True)
            self.newbuild_available.setdefault(name, True)
            self.conversion_available.setdefault(name, True)

            for technology in self.technologies:
                self.initial_technology_share.setdefault((name, technology.name), None)

        for technology in self.technologies:
            self.newbuild_technology_limit.setdefault(technology.name, Scalar(1.0))
            self.retrofit_technology_limit.setdefault(technology.name, Scalar(1.0))

    def initialize_expectation(self, length: int, fuels: dict[str, Fuel]) -> None:
        vessel_names = [vessel.name for vessel in self.vessels]
        self.expectation.initialize(length, vessel_names, fuels)

    def initialize_results(
        self,
        context: ResultsContext,
        regulation_names: Sequence[str],
        levy_names: Sequence[str],
    ) -> None:
        vessel_names = [vessel.name for vessel in self.vessels]
        technology_names = [technology.name for technology in self.technologies]

        self.results.initialize(
            context, vessel_names, technology_names, regulation_names, levy_names
        )

    def can_retrofit(self) -> bool:
        return bool(self.technologies)

    def can_fuel_convert(self) -> bool:
        return any(value is not None for value in self.fuel_conversion_cost.values())

    def get_number_of_packages(self) -> int:
        # the packages are cumulative and start from the empty one, so their count
        # is known from the technologies before the packages themselves are built
        return len(self.technologies) + 1
