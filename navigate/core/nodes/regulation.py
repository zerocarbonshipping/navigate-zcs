# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar, as_scalar, assign_id, assign_value, command_assignment_to_dict
from navigate.core.assign import BOOL_ID
from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.core.expectations import RegulationExpectation
from navigate.core.node_type import FORECAST, REGULATION, VARIABLE
from navigate.core.nodes._policy import _Policy
from navigate.core.profiles import RegulationProfile
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel


class Regulation(_Policy):
    def __init__(self, name):
        super().__init__(name, REGULATION)

        self.measure = None            # enum, ID of emissions measure

        self.intra_fraction = None     # float, fraction of emissions on intra travel accounted for
        self.inter_fraction = None     # float, fraction of emissions on inter travel accounted for
        self.extra_fraction = None     # float, fraction of emissions on extra travel accounted for

        # remedial compliance
        self.remedial_cost = None      # float, cost per remedial unit, USD/ton

        # flexibility cost belief
        self.flexibility_horizon = None  # float, belief horizon for the flexibility cost, years

        # threshold
        self.vessel_threshold = {}     # dict[vessel_name: float], individual threshold per vessel

        # capacity (measure specific)
        self.vessel_capacity = {}      # dict[vessel_name: float], capacity per vessel if impact is vessel

        # threshold adjustment
        self.allow_threshold_adjustment = False  # bool, if True, bunker algorithm adjusts thresholds on non-compliance

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_scheme(self, scheme):
        """
        Set the scheme of the regulation.

        If 'INDIVIDUAL' then vessels cannot trade emission units with each other to comply.
        If 'FLEXIBLE' then vessels can trade emission units with each other to comply.

        Examples
        --------
        - INDIVIDUAL
        - FLEXIBLE

        Parameters
        ----------
        scheme : str
            Regulation scheme.
        """

        self.scheme = assign_id(scheme, RegulationSchemeID)

    def set_measure(self, measure):
        """
        Set the emission measure of the regulation.

        If 'ABSOLUTE' the absolute emissions in tons/year are targeted.
        If 'INTENSITY' the emission intensity in g/MJ are targeted.
        If 'TRANSPORT' the carbon intensity index in gCO2-eq/actual cargo-miles is targeted.
        If 'TRANSPORT_NOMINAL' the carbon intensity index in gCO2-eq/nominal cargo-miles is targeted.

        Examples
        --------
        - ABSOLUTE
        - INTENSITY
        - TRANSPORT
        - TRANSPORT_NOMINAL

        Parameters
        ----------
        measure : str
            Emission measure.
        """

        self.measure = assign_id(measure, RegulationMeasureID)

    def set_intra_fraction(self, intra_fraction):
        """
        Set the fraction for how much of the emissions between two ports
        inside (intra) the jurisdiction should be counted in the calculation.

        Examples
        --------
        - 0.5

        Parameters
        ----------
        intra_fraction : float | NodeReference
            Fraction of emissions counted during intra jurisdiction travel.
        """

        self.intra_fraction = assign_value(as_scalar(intra_fraction), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_inter_fraction(self, inter_fraction):
        """
        Set the fraction for how much of the emissions between two ports
        where one is in the jurisdiction and the other outside the
        jurisdiction (inter) should be counted in the calculation.

        Examples
        --------
        - 0.5

        Parameters
        ----------
        inter_fraction : float | NodeReference
            Fraction of emissions counted during inter jurisdiction travel.
        """

        self.inter_fraction = assign_value(as_scalar(inter_fraction), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_extra_fraction(self, extra_fraction):
        """
        Set the fraction for how much of the emissions between two ports
        outside the jurisdiction (extra) should be counted in the calculation.

        Examples
        --------
        - 0.5

        Parameters
        ----------
        extra_fraction : float | NodeReference
            Fraction of emissions counted during extra jurisdiction travel.
        """

        self.extra_fraction = assign_value(as_scalar(extra_fraction), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_remedial_cost(self, remedial_cost):
        """
        Set the cost of purchasing a remedial compliance unit in USD/ton emission.

        Examples
        --------
        - 1e3
        - Forecast("name")

        Parameters
        ----------
        remedial_cost : float | NodeReference
            Cost of a remedial unit.
        """

        self.remedial_cost = assign_value(as_scalar(remedial_cost), type_=(FORECAST, VARIABLE), lower=0.)

    def set_flexibility_horizon(self, flexibility_horizon):
        """
        Set the decision horizon, in years, used to smooth the belief of the flexibility cost that enters
        the expected policy expenses of the policed vessels.

        A longer horizon makes the belief respond more slowly to changes in the flexibility cost between
        outer time-steps, preventing small changes in future fuel availability from translating into
        expectations of large flexibility-cost differences.

        Examples
        --------
        - 3.0
        - Forecast("name")

        Parameters
        ----------
        flexibility_horizon : float | NodeReference
            Decision horizon for the flexibility cost belief, in years.
        """

        self.flexibility_horizon = assign_value(as_scalar(flexibility_horizon), type_=(FORECAST, VARIABLE), lower=0.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_vessel_threshold(self, vessel_name, threshold):
        """
        Set the threshold that a specific vessel must satisfy in the measure unit.

        If 'ABSOLUTE' the threshold is on absolute emissions in tons/year.
        If 'INTENSITY' the threshold is on emission intensity in g/MJ.
        If 'TRANSPORT' the threshold is on carbon intensity index in gCO2-eq/actual cargo-miles.
        If 'TRANSPORT_NOMINAL' the threshold is on carbon intensity index in gCO2-eq/nominal cargo-miles.

        Every vessel included in the regulation must have a threshold; use the wildcard "*" to assign the
        same threshold to all vessels. If 'Scheme' is 'FLEXIBLE' the per-vessel thresholds pool into a
        single fleet-level constraint.

        Examples
        --------
        - "name", 1e3
        - "*", Forecast("forecast_name")

        Parameters
        ----------
        vessel_name : str
            Name of vessel for which the threshold is assigned.
        threshold : float | NodeReference
            Threshold for a vessel.
        """

        command_assignment_to_dict(vessel_name, threshold, self.vessel_threshold, type_=(FORECAST, VARIABLE), lower=0.)

    def set_vessel_capacity(self, vessel_name, capacity):
        """
        Set the capacity of a specific vessel for use in transport calculations.

        This is only relevant if 'Measure' is set to 'TRANSPORT_NOMINAL' or 'TRANSPORT'.

        Examples
        --------
        - "name", 35000
        - "vessel_name", Forecast("forecast_name")

        Parameters
        ----------
        vessel_name : str
            Name of vessel for which the capacity is assigned.
        capacity : float | NodeReference
            Capacity of a vessel.
        """

        command_assignment_to_dict(vessel_name, capacity, self.vessel_capacity, type_=(FORECAST, VARIABLE), lower=0.)

    def set_allow_threshold_adjustment(self, allow_threshold_adjustment):
        """
        Set whether the regulation threshold should be automatically adjusted when the bunker algorithm
        detects non-compliance. If enabled, the bunker algorithm will perform a multi-step solve where
        it first solves normally, then adjusts the threshold to match achievable compliance levels,
        and re-solves with the adjusted thresholds.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        allow_threshold_adjustment : str
            Whether to allow threshold adjustment (TRUE/FALSE).
        """

        self.allow_threshold_adjustment = assign_id(allow_threshold_adjustment, BOOL_ID)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        self._initialize_policy()

        if self.scheme is None:
            no_value_assigned_error(self, 'Scheme')

        if self.measure is None:
            no_value_assigned_error(self, 'Measure')

        if self.intra_fraction is None:
            self.intra_fraction = Scalar(1)

        if self.inter_fraction is None:
            self.inter_fraction = Scalar(1)

        if self.extra_fraction is None:
            self.extra_fraction = Scalar(0)

        if self.remedial_cost is None:
            self.remedial_cost = Scalar(0)

        if self.flexibility_horizon is None:
            self.flexibility_horizon = Scalar(3)

        for vessel_name, include_vessel in self.include_vessel.items():

            if include_vessel and (self.vessel_threshold[vessel_name] is None):

                raise ValueError("{}: Vessel(\"{}\") is included in the regulation but"
                                 " no vessel_threshold is defined.".format(self, vessel_name))

    def initialize_dependencies(self, vessels):

        for vessel_name in vessels:
            if vessel_name not in self.vessel_threshold:
                self.vessel_threshold[vessel_name] = None
                self.vessel_capacity[vessel_name] = None

        self._initialize_policy_dependencies(vessels)

    def initialize_expectation(self, length: int, vessels: dict[str, Vessel]) -> None:
        self.expectation = RegulationExpectation()
        self.expectation.initialize(length, [e.name for e in self.emissions], vessels)

    def initialize_profile(self, timeline: np.ndarray, vessels: dict[str, Vessel]) -> None:

        self.profile = RegulationProfile()
        self.profile.initialize(timeline, vessels)

    def calculate_expectation(self, emissions, vessels, emissions_lifetime, timeline, idx):

        if not self.active:
            return

        times = timeline[idx:]

        self.expectation.set_remedial_cost(idx, self.remedial_cost.get(times))

        if self.measure in (RegulationMeasureID.TRANSPORT, RegulationMeasureID.TRANSPORT_NOMINAL):

            for vessel_name, capacity in self.vessel_capacity.items():

                if capacity is not None:
                    self.expectation.set_vessel_capacity(idx, vessel_name, capacity.get(times))

                else:
                    nominal_capacity = vessels[vessel_name].nominal_capacity.get(times)
                    self.expectation.set_vessel_capacity(idx, vessel_name, nominal_capacity)

        self._calculate_policy_expectations(self.expectation, emissions, emissions_lifetime)

    def calculate_profile(self, idx):

        if not self.active:
            return

        self.profile.set_remedial_cost(idx, self.remedial_cost.get())

        for vessel_name, threshold in self.vessel_threshold.items():

            if self.vessel_is_policed(vessel_name):
                self.profile.set_vessel_threshold(idx, vessel_name, threshold.get())
