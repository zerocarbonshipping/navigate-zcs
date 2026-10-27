# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Levy node, a penalty or subsidy on emission factors at port."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_scalar,
    assign_id,
    assign_value,
    deck_attribute,
)
from navigate.core.enum_ import LevySchemeID
from navigate.core.expectations import LevyExpectation
from navigate.core.node_type import FORECAST, LEVY, VARIABLE
from navigate.core.nodes._policy import _Policy
from navigate.core.results import LevyResults

if TYPE_CHECKING:
    from navigate.core.results import ResultsContext
    from navigate.core.types_ import ForecastArgument, ForecastInput
    from navigate.util.types_ import DateArray, FloatArray


class Levy(_Policy):
    """A levy penalizing or subsidizing fuels by emission factor against thresholds."""

    type = LEVY

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.scheme: LevySchemeID
        self.level: ForecastInput = Scalar(0.0)
        self.lower_threshold: ForecastInput = Scalar(0.0)
        self.upper_threshold: ForecastInput | None = None

        # internal variables -----------------------------------------------------------
        self.expectation: LevyExpectation = LevyExpectation()
        self.results: LevyResults = LevyResults()

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE, required=True)
    def set_scheme(self, scheme: str) -> None:
        """Set the scheme of the levy."""
        self.scheme = assign_id(scheme, LevySchemeID)

    @deck_attribute()
    def set_level(self, level: ForecastArgument) -> None:
        """Set the levy level paid or received, depending on scheme."""
        self.level = assign_value(
            as_scalar(level), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_lower_threshold(self, lower_threshold: ForecastArgument) -> None:
        """Set the lower emission factor threshold of the levy."""
        self.lower_threshold = assign_value(
            as_scalar(lower_threshold), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_upper_threshold(self, upper_threshold: ForecastArgument) -> None:
        """Set the upper emission factor threshold of the levy."""
        self.upper_threshold = assign_value(
            as_scalar(upper_threshold), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def initialize_expectation(self, length: int) -> None:
        emission_names = [emission.name for emission in self.emissions]
        self.expectation.initialize(length, emission_names)

    def initialize_results(self, context: ResultsContext) -> None:
        self.results.initialize(context)

    def check_dynamic_consistency(self, times: FloatArray, dates: DateArray) -> None:
        # SUBSIDY never reads the upper threshold, and an inactive levy is
        # checked from the step an event activates it
        if self.upper_threshold is None:
            return
        if not self.active:
            return
        if self.scheme == LevySchemeID.SUBSIDY:
            return

        lower = self.lower_threshold.get(times)
        upper = self.upper_threshold.get(times)
        crossed = np.flatnonzero(upper < lower)

        if crossed.size:
            date = dates[crossed[0]]
            raise ValueError(
                f"{self}: 'UpperThreshold' must be >= 'LowerThreshold' at every "
                f"time step, but is below it at {date}."
            )
