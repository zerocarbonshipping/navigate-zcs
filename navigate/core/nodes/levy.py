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
    from navigate.core.nodes.input_kinds import ForecastInput
    from navigate.core.nodes.vessel import Vessel
    from navigate.util import FloatArray


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
        """
        Set the scheme of the levy.

        If 'PENALTY' then the fuel is penalized for emission factors above the
        threshold. If 'SUBSIDY' then the fuel is subsidized for emission factors below
        the threshold. If 'BOTH' then the fuel is penalized above and subsidized below
        the threshold.

        Examples
        --------
        - PENALTY
        - SUBSIDY
        - BOTH

        Parameters
        ----------
        scheme
            Levy scheme.
        """
        self.scheme = assign_id(scheme, LevySchemeID)

    def set_level(self, level: float | ForecastInput) -> None:
        """
        Set the levy level paid or received, depending on scheme, in USD/ton emission.

        Examples
        --------
        - 100
        - Forecast("name")

        Parameters
        ----------
        level
            Cost/remuneration of the levy.
        """
        self.level = assign_value(
            as_scalar(level), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_lower_threshold(self, lower_threshold: float | ForecastInput) -> None:
        """
        Set the lower emission factor threshold of the levy in kg emissions / GJ.

        Emissions below this threshold are not penalized (for PENALTY/BOTH scheme) and
        emissions above are not subsidized (for SUBSIDY/BOTH scheme).

        Examples
        --------
        - 91.2
        - Forecast("name")

        Parameters
        ----------
        lower_threshold
            Lower emission factor threshold.
        """
        self.lower_threshold = assign_value(
            as_scalar(lower_threshold), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_upper_threshold(self, upper_threshold: float | ForecastInput) -> None:
        """
        Set the upper emission factor threshold of the levy in kg emissions / GJ.

        Emissions above this threshold are not additionally penalized (for PENALTY/BOTH
        scheme). The penalty is only paid for emissions between the lower and upper
        threshold. If not set, there is no upper cap on the penalty.

        Examples
        --------
        - 91.2
        - Forecast("name")

        Parameters
        ----------
        upper_threshold
            Upper emission factor threshold.
        """
        self.upper_threshold = assign_value(
            as_scalar(upper_threshold), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        super().check_consistency()

        if self.upper_threshold is not None:
            upper = self.upper_threshold.get()
            lower = self.lower_threshold.get()
            # a Forecast answers nan until the first time step, so
            # the check only applies to thresholds known up front
            if not np.isnan(upper) and not np.isnan(lower) and upper < lower:
                raise ValueError(
                    f"{self}: 'UpperThreshold' must be >= 'LowerThreshold'."
                )

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
