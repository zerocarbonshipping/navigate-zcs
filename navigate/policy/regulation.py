# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar, as_scalar, assign_id, assign_value, command_assignment_to_dict
from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.core.expectations import RegulationExpectation
from navigate.core.id_ import FORECAST, REGULATION, VARIABLE
from navigate.core.misc import BOOL_ID
from navigate.core.profiles import RegulationProfile
from navigate.exceptions import no_value_assigned_error
from navigate.policy._policy import Policy

if TYPE_CHECKING:
    from navigate.vessel import Vessel


class Regulation(Policy):
    def __init__(self, name):
        super().__init__(name)

        self._type = REGULATION

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
        self.shared_threshold = None   # float, shared threshold for all vessels

        # capacity (measure specific)
        self.vessel_capacity = {}      # dict[vessel_name: float], capacity per vessel if impact is vessel

        # threshold adjustment
        self.allow_threshold_adjustment = False  # bool, if True, bunker algorithm adjusts thresholds on non-compliance

        # offset threshold
        self.offset_threshold = None   # threshold to which offsets can cover down to, in measure unit

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_scheme(self, scheme):
        """
        Set the scheme of the regulation.

        If 'INDIVIDUAL' then vessels cannot trade emission units with each other to comply.
        If 'FLEXIBILITY' then vessels can trade emission units with each other to comply.

        Examples
        --------
        - INDIVIDUAL
        - FLEXIBILITY

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

    def set_shared_threshold(self, shared_threshold):
        """
        Set the shared threshold across all vessels of the regulation in the measure unit.

        If 'ABSOLUTE' the threshold is on absolute emissions in tons/year.
        If 'INTENSITY' the threshold is on emission intensity in g/MJ.

        Notice that if the measure is 'ABSOLUTE' then the threshold is the total allowed emissions for all vessels, not
        per individual vessel. If the measure is 'INTENSITY' then the threshold is the same for all vessels as it is
        per energy consumed by the individual vessel.

        Notice that this overwrites any individual vessel thresholds set via 'set_vessel_threshold'.

        Examples
        --------
        - 1e6
        - Forecast("name")

        Parameters
        ----------
        shared_threshold : float | NodeReference
            Threshold shared across all vessels under the regulation.
        """

        self.shared_threshold = assign_value(as_scalar(shared_threshold), type_=(FORECAST, VARIABLE), lower=0.)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_vessel_threshold(self, vessel_name, threshold):
        """
        Set the threshold that a specific vessel must satisfy in the measure unit.

        If 'ABSOLUTE' the threshold is on absolute emissions in tons/year.
        If 'INTENSITY' the threshold is on emission intensity in g/MJ.
        If 'TRANSPORT' the threshold is on carbon intensity index in gCO2-eq/actual cargo-miles.
        If 'TRANSPORT_NOMINAL' the threshold is on carbon intensity index in gCO2-eq/nominal cargo-miles.

        Examples
        --------
        - "name", 1e3
        - "vessel_name", Forecast("forecast_name")

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

    def set_offset_threshold(self, offset_threshold):
        """
        Set the offset threshold in the regulation's measure unit.

        This defines the emission level to which offsets can cover down to. Vessels can offset
        non-compliance from their actual emissions down to this threshold. Below this level,
        genuine emission reductions or remedial costs are required.

        If not set, defaults to the SharedThreshold value, meaning all non-compliance above the
        regulation threshold can be offset (current default behavior).

        Examples
        --------
        - 10
        - Forecast("offset_target")

        Parameters
        ----------
        offset_threshold : float | NodeReference
            Offset threshold in the regulation's measure unit.
        """

        self.offset_threshold = assign_value(as_scalar(offset_threshold), type_=(FORECAST, VARIABLE), lower=0.)

    def get_effective_offset_threshold(self):
        """Return the offset threshold, defaulting to the shared threshold if not explicitly set."""
        if self.offset_threshold is not None:
            return self.offset_threshold
        return self.shared_threshold

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

            if include_vessel:

                if self.measure in (RegulationMeasureID.ABSOLUTE, RegulationMeasureID.INTENSITY):

                    # ensure the regulated vessel has a threshold
                    if (self.vessel_threshold[vessel_name] is None) and (self.shared_threshold is None):

                        raise ValueError("{}: Vessel(\"{}\") is included in the regulation but neither a"
                                         " vessel_threshold nor a SharedThreshold is set.".format(self, vessel_name))

                elif self.measure in (RegulationMeasureID.TRANSPORT, RegulationMeasureID.TRANSPORT_NOMINAL):

                    # ensure the regulated vessel has a threshold
                    if self.vessel_threshold[vessel_name] is None:

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
        self.expectation.initialize(length, [e.get_name() for e in self.emissions], vessels)

    def initialize_profile(self, timeline: np.ndarray, vessels: dict[str, Vessel],
                           emissions_lifetime: float) -> None:

        self.profile = RegulationProfile()
        self.profile.initialize(timeline, vessels, self.fuels, self.emissions, emissions_lifetime)

    def calculate_expectation(self, emissions, vessels, emissions_lifetime, timeline, idx, offsetting_cost=None):

        if not self.active:
            return

        times = timeline[idx:]

        remedial_cost = self.remedial_cost.get(times)

        if self.allow_offsetting and offsetting_cost is not None:
            remedial_cost = np.minimum(remedial_cost, offsetting_cost)

        self.expectation.set_remedial_cost(idx, remedial_cost)

        if self.shared_threshold is not None:
            self.expectation.set_shared_threshold(idx, self.shared_threshold.get(times))

        # notice that vessel specific thresholds are set in the '/policy/threshold.py' file

        if self.measure in (RegulationMeasureID.TRANSPORT, RegulationMeasureID.TRANSPORT_NOMINAL):

            for vessel_name, capacity in self.vessel_capacity.items():

                if capacity is not None:
                    self.expectation.set_vessel_capacity(idx, vessel_name, capacity.get(times))

                else:
                    nominal_capacity = vessels[vessel_name].nominal_capacity.get(times)
                    self.expectation.set_vessel_capacity(idx, vessel_name, nominal_capacity)

        self._calculate_policy_expectations(self.expectation, emissions, emissions_lifetime)

    def calculate_profile(self, timeline, idx):

        if not self.active:
            return

        self.profile.set_remedial_cost(idx, self.remedial_cost.get())

        if self.shared_threshold is not None:
            self.profile.set_shared_threshold(idx, self.shared_threshold.get())

        self._calculate_policy_profile(idx, timeline)

    def get_vessel_threshold(self, vessel_name):
        return self.vessel_threshold[vessel_name]
