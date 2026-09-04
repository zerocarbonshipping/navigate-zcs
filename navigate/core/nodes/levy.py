# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np

from navigate.core import Scalar, as_scalar, assign_id, assign_value
from navigate.core.enum_ import LevySchemeID
from navigate.core.expectations import LevyExpectation
from navigate.core.node_type import FORECAST, LEVY, VARIABLE
from navigate.core.nodes._policy import _Policy
from navigate.core.profiles import LevyProfile
from navigate.exceptions import no_value_assigned_error


class Levy(_Policy):
    def __init__(self, name):
        super().__init__(name, LEVY)

        self.level = None              # dict[vessel_name: float], level of the levy, USD/ton emission
        self.lower_threshold = None    # float, reference emissions factor between penalty and subsidy
        self.upper_threshold = None    # float, upper cap on emission factor for penalty calculation

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_scheme(self, scheme):
        """
        Set the scheme of the levy.

        If 'PENALTY' then the fuel is penalized for emission factors above the threshold.
        If 'SUBSIDY' then the fuel is subsidized for emission factors below the threshold.
        If 'BOTH' then the fuel is penalized above and subsidized below the threshold.

        Examples
        --------
        - PENALTY
        - SUBSIDY
        - BOTH

        Parameters
        ----------
        scheme : str
            Levy scheme.
        """

        self.scheme = assign_id(scheme, LevySchemeID)

    def set_level(self, level):
        """
        Set the level of the levy being paid or received dependent on the scheme in USD/ton emission.

        Examples
        --------
        - 100
        - Forecast("name")

        Parameters
        ----------
        level : float | NodeReference
            Cost/remuneration of the levy.
        """

        self.level = assign_value(as_scalar(level), type_=(FORECAST, VARIABLE), lower=0.)

    def set_lower_threshold(self, lower_threshold):
        """
        Set the lower emission factor threshold of the levy in kg emissions / GJ.

        Emissions below this threshold are not penalized (for PENALTY/BOTH scheme) and emissions above are not
        subsidized (for SUBSIDY/BOTH scheme).

        Examples
        --------
        - 91.2
        - Forecast("name")

        Parameters
        ----------
        lower_threshold : float | NodeReference
            Lower emission factor threshold.
        """

        self.lower_threshold = assign_value(as_scalar(lower_threshold), type_=(FORECAST, VARIABLE), lower=0.)

    def set_upper_threshold(self, upper_threshold):
        """
        Set the upper emission factor threshold of the levy in kg emissions / GJ.

        Emissions above this threshold are not additionally penalized (for PENALTY/BOTH scheme). The penalty is only
        paid for emissions between the lower and upper threshold. If not set, there is no upper cap on the penalty.

        Examples
        --------
        - 91.2
        - Forecast("name")

        Parameters
        ----------
        upper_threshold : float | NodeReference
            Upper emission factor threshold.
        """

        self.upper_threshold = assign_value(as_scalar(upper_threshold), type_=(FORECAST, VARIABLE), lower=0.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        self._initialize_policy()

        if self.scheme is None:
            no_value_assigned_error(self, 'Scheme')

        if self.lower_threshold is None:
            self.lower_threshold = Scalar(0)

        if self.upper_threshold is not None:
            upper = self.upper_threshold.get()
            lower = self.lower_threshold.get()
            if upper is not None and lower is not None and upper < lower:
                raise ValueError("{}: 'UpperThreshold' must be >= 'LowerThreshold'.".format(self))

        if self.level is None:
            self.level = Scalar(0)

    def initialize_dependencies(self, vessels):
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        vessels : dict[str, Vessel]
            All vessels in the simulation.
        """

        self._initialize_policy_dependencies(vessels)

    def initialize_expectation(self, length: int) -> None:
        self.expectation = LevyExpectation()
        self.expectation.initialize(length, [e.name for e in self.emissions])

    def initialize_profile(self, timeline: np.ndarray) -> None:

        self.profile = LevyProfile()
        self.profile.initialize(timeline)

    def calculate_expectation(self, emissions, emissions_lifetime, timeline, idx):

        if not self.active:
            return

        self.expectation.set_level(idx, self.level.get(timeline[idx:]))

        self._calculate_policy_expectations(self.expectation, emissions, emissions_lifetime)
