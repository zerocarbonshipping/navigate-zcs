# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Levy node, a penalty or subsidy on emission factors at port."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar, as_scalar, assign_id, assign_value
from navigate.core.enum_ import LevySchemeID
from navigate.core.expectations import LevyExpectation
from navigate.core.node_type import FORECAST, LEVY, VARIABLE
from navigate.core.nodes._policy import _Policy
from navigate.core.profiles import LevyProfile

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastArgument, ForecastInput
    from navigate.util import DateArray, FloatArray


class Levy(_Policy):
    """A levy penalizing or subsidizing fuels by emission factor against thresholds."""

    def __init__(self, name: str) -> None:
        super().__init__(name, LEVY)

        # external variables -----------------------------------------------------------
        self.level: ForecastInput = Scalar(0.0)
        self.lower_threshold: ForecastInput = Scalar(0.0)
        self.upper_threshold: ForecastInput | None = None

        # internal variables -----------------------------------------------------------
        self.expectation: LevyExpectation = LevyExpectation()
        self.profile: LevyProfile = LevyProfile()

    # external methods (DSL attributes) ------------------------------------------------
    def set_scheme(self, scheme: str) -> None:
        """Set the scheme of the levy."""
        self.scheme = assign_id(scheme, LevySchemeID)

    def set_level(self, level: ForecastArgument) -> None:
        """Set the levy level paid or received, depending on scheme."""
        self.level = assign_value(
            as_scalar(level), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_lower_threshold(self, lower_threshold: ForecastArgument) -> None:
        """Set the lower emission factor threshold of the levy."""
        self.lower_threshold = assign_value(
            as_scalar(lower_threshold), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_upper_threshold(self, upper_threshold: ForecastArgument) -> None:
        """Set the upper emission factor threshold of the levy."""
        self.upper_threshold = assign_value(
            as_scalar(upper_threshold), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def initialize_dependencies(self, vessels: dict[str, Vessel]) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        vessels
            All vessels in the simulation.
        """
        self._initialize_policy_dependencies(vessels)

    def initialize_expectation(self, length: int) -> None:
        self.expectation.initialize(length, [e.name for e in self.emissions])

    def initialize_profile(self, timeline: FloatArray) -> None:
        self.profile.initialize(timeline)

    def check_dynamic_consistency(self, times: FloatArray, dates: DateArray) -> None:
        super().check_dynamic_consistency(times, dates)

        # nothing to compare without an UpperThreshold; an inactive levy is
        # checked once an event activates it, over timeline[idx:] from that
        # step; a SUBSIDY scheme never reads upper_threshold in the levy
        # coefficient
        if self.upper_threshold is None:
            return
        if not self.is_active():
            return
        if self.scheme == LevySchemeID.SUBSIDY:
            return

        lower = self.lower_threshold.get(times)
        upper = self.upper_threshold.get(times)
        crossed = np.flatnonzero(upper < lower)
        if crossed.size:
            i = crossed[0]
            raise ValueError(
                f"{self}: 'UpperThreshold' must be >= 'LowerThreshold' at every "
                f"time step, but is below it at {dates[i]}."
            )

    def calculate_expectation(
        self,
        emissions: dict[str, Emission],
        emissions_lifetime: float,
        timeline: FloatArray,
        idx: int,
    ) -> None:

        if not self.active:
            return

        self.expectation.set_level(idx, self.level.get(timeline[idx:]))

        self._calculate_policy_expectations(
            self.expectation, emissions, emissions_lifetime
        )
