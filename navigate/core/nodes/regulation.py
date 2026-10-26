# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Regulation node, an emission target vessels must comply with."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_scalar,
    assign_boolean,
    assign_id,
    assign_value,
    deck_attribute,
    deck_command,
    write_matching_keys,
)
from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.core.expectations import RegulationExpectation
from navigate.core.node_type import FORECAST, REGULATION, VARIABLE
from navigate.core.nodes._policy import _Policy
from navigate.core.results import RegulationResults

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.results import ResultsContext
    from navigate.core.types_ import ForecastArgument, ForecastInput

logger = logging.getLogger(__name__)


class Regulation(_Policy):
    """A regulation holding policed vessels to an emission threshold in its measure."""

    type = REGULATION

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.scheme: RegulationSchemeID
        self.measure: RegulationMeasureID

        self.intra_fraction: ForecastInput = Scalar(1.0)
        self.inter_fraction: ForecastInput = Scalar(1.0)
        self.extra_fraction: ForecastInput = Scalar(0.0)

        self.remedial_cost: ForecastInput = Scalar(0.0)
        self.flexibility_horizon: ForecastInput = Scalar(3.0)

        self.allow_threshold_adjustment: bool = False

        self.vessel_threshold: dict[str, ForecastInput | None] = {}
        self.vessel_capacity: dict[str, ForecastInput | None] = {}

        # internal variables -----------------------------------------------------------
        self.expectation: RegulationExpectation = RegulationExpectation()
        self.results: RegulationResults = RegulationResults()

        # set on assignment, cleared once the unused-under-this-scheme warning fires
        self._flexibility_horizon_unreported: bool = False

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_scheme(self, scheme: str) -> None:
        """Set the scheme of the regulation."""
        self.scheme = assign_id(scheme, RegulationSchemeID)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_measure(self, measure: str) -> None:
        """Set the emission measure of the regulation."""
        self.measure = assign_id(measure, RegulationMeasureID)

    @deck_attribute()
    def set_intra_fraction(self, intra_fraction: ForecastArgument) -> None:
        """Set the fraction of emissions counted for intra-jurisdiction travel."""
        self.intra_fraction = assign_value(
            as_scalar(intra_fraction), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute()
    def set_inter_fraction(self, inter_fraction: ForecastArgument) -> None:
        """Set the fraction of emissions counted for inter-jurisdiction travel."""
        self.inter_fraction = assign_value(
            as_scalar(inter_fraction), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute()
    def set_extra_fraction(self, extra_fraction: ForecastArgument) -> None:
        """Set the fraction of emissions counted for extra-jurisdiction travel."""
        self.extra_fraction = assign_value(
            as_scalar(extra_fraction), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    @deck_attribute()
    def set_remedial_cost(self, remedial_cost: ForecastArgument) -> None:
        """Set the cost of purchasing a remedial compliance unit."""
        self.remedial_cost = assign_value(
            as_scalar(remedial_cost), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_flexibility_horizon(self, flexibility_horizon: ForecastArgument) -> None:
        """Set the decision horizon smoothing the flexibility-cost belief."""
        self.flexibility_horizon = assign_value(
            as_scalar(flexibility_horizon), type_=(FORECAST, VARIABLE), lower=0.0
        )
        self._flexibility_horizon_unreported = True

    @deck_attribute()
    def set_allow_threshold_adjustment(self, allow_threshold_adjustment: str) -> None:
        """Set whether the threshold is automatically adjusted on non-compliance."""
        self.allow_threshold_adjustment = assign_boolean(allow_threshold_adjustment)

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_vessel_threshold(
        self, vessel_name: str, threshold: ForecastArgument
    ) -> None:
        """Set the threshold that a specific vessel must satisfy."""
        write_matching_keys(
            vessel_name,
            assign_value(as_scalar(threshold), type_=(FORECAST, VARIABLE), lower=0.0),
            self.vessel_threshold,
        )

    @deck_command()
    def set_vessel_capacity(self, vessel_name: str, capacity: ForecastArgument) -> None:
        """Set the capacity of a specific vessel for use in transport calculations."""
        write_matching_keys(
            vessel_name,
            assign_value(as_scalar(capacity), type_=(FORECAST, VARIABLE), lower=0.0),
            self.vessel_capacity,
        )

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        super().check_consistency()

        for vessel_name, include_vessel in self.include_vessel.items():
            if include_vessel and self.vessel_threshold[vessel_name] is None:
                raise ValueError(
                    f'{self}: Vessel("{vessel_name}") is included in the regulation but'
                    " no vessel_threshold is defined."
                )

        is_flexible = self.scheme == RegulationSchemeID.FLEXIBLE
        if self._flexibility_horizon_unreported and not is_flexible:
            logger.warning(
                "%s: 'FlexibilityHorizon' is assigned but is unused for Scheme = %s.",
                self,
                self.scheme.name,
            )

            self._flexibility_horizon_unreported = False

    def initialize_dependencies(self, vessels: dict[str, Vessel]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        vessels
            All vessels in the simulation.
        """
        for vessel_name in vessels:
            self.vessel_threshold.setdefault(vessel_name, None)
            self.vessel_capacity.setdefault(vessel_name, None)

        super().initialize_dependencies(vessels)

    def initialize_expectation(
        self, length: int, routes: dict[str, Route], vessels: dict[str, Vessel]
    ) -> None:
        emission_names = [emission.name for emission in self.emissions]
        self.expectation.initialize(length, emission_names, routes, vessels)

    def initialize_results(
        self, context: ResultsContext, vessel_names: Sequence[str]
    ) -> None:
        self.results.initialize(context, vessel_names)
