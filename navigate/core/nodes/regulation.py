# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_boolean,
    assign_id,
    assign_value,
    command_assignment_to_dict,
)
from navigate.core.enum_ import RegulationMeasureID, RegulationSchemeID
from navigate.core.expectations import RegulationExpectation
from navigate.core.node_type import FORECAST, REGULATION, VARIABLE
from navigate.core.nodes._policy import _Policy
from navigate.core.profiles import RegulationProfile
from navigate.exceptions import no_value_assigned_error

if TYPE_CHECKING:
    import numpy as np

    from navigate.core.nodes.input_kinds import ForecastInput
    from navigate.core.nodes.vessel import Vessel


class Regulation(_Policy):
    def __init__(self, name: str) -> None:
        super().__init__(name, REGULATION)

        # external variables -----------------------------------------------------------
        self._measure: RegulationMeasureID | None = None

        self.intra_fraction: ForecastInput = Scalar(1.0)
        self.inter_fraction: ForecastInput = Scalar(1.0)
        self.extra_fraction: ForecastInput = Scalar(0.0)

        # remedial compliance
        self.remedial_cost: ForecastInput = Scalar(0.0)

        # flexibility cost belief
        self.flexibility_horizon: ForecastInput = Scalar(3.0)

        # threshold
        self.vessel_threshold: dict[str, ForecastInput | None] = {}

        # capacity (measure specific)
        self.vessel_capacity: dict[str, ForecastInput | None] = {}

        # threshold adjustment
        self.allow_threshold_adjustment: bool = False

        # internal variables -----------------------------------------------------------
        self.expectation: RegulationExpectation = RegulationExpectation()
        self.profile: RegulationProfile = RegulationProfile()

    # external methods (DSL attributes) ------------------------------------------------
    def set_scheme(self, scheme):
        """
        Set the scheme of the regulation.

        If 'INDIVIDUAL' then vessels cannot trade emission units with each other to
        comply. If 'FLEXIBLE' then vessels can trade emission units with each other to
        comply.

        Examples
        --------
        - INDIVIDUAL
        - FLEXIBLE

        Parameters
        ----------
        scheme : str
            Regulation scheme.
        """
        self._scheme = assign_id(scheme, RegulationSchemeID)

    def set_measure(self, measure):
        """
        Set the emission measure of the regulation.

        If 'ABSOLUTE' the absolute emissions in tons/year are targeted. If 'INTENSITY'
        the emission intensity in g/MJ are targeted. If 'TRANSPORT' the carbon intensity
        index in gCO2-eq/actual cargo-miles is targeted. If 'TRANSPORT_NOMINAL' the
        carbon intensity index in gCO2-eq/nominal cargo-miles is targeted.

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
        self._measure = assign_id(measure, RegulationMeasureID)

    def set_intra_fraction(self, intra_fraction):
        """
        Set the fraction of emissions counted for intra-jurisdiction travel.

        Intra travel is between two ports inside the jurisdiction.

        Examples
        --------
        - 0.5

        Parameters
        ----------
        intra_fraction : float | Node
            Fraction of emissions counted during intra jurisdiction travel.
        """
        self.intra_fraction = assign_value(
            as_scalar(intra_fraction), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    def set_inter_fraction(self, inter_fraction):
        """
        Set the fraction of emissions counted for inter-jurisdiction travel.

        Inter travel is between two ports where one is in the jurisdiction and the other
        is outside it.

        Examples
        --------
        - 0.5

        Parameters
        ----------
        inter_fraction : float | Node
            Fraction of emissions counted during inter jurisdiction travel.
        """
        self.inter_fraction = assign_value(
            as_scalar(inter_fraction), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    def set_extra_fraction(self, extra_fraction):
        """
        Set the fraction of emissions counted for extra-jurisdiction travel.

        Extra travel is between two ports both outside the jurisdiction.

        Examples
        --------
        - 0.5

        Parameters
        ----------
        extra_fraction : float | Node
            Fraction of emissions counted during extra jurisdiction travel.
        """
        self.extra_fraction = assign_value(
            as_scalar(extra_fraction), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    def set_remedial_cost(self, remedial_cost):
        """
        Set the cost of purchasing a remedial compliance unit in USD/ton emission.

        Examples
        --------
        - 1e3
        - Forecast("name")

        Parameters
        ----------
        remedial_cost : float | Node
            Cost of a remedial unit.
        """
        self.remedial_cost = assign_value(
            as_scalar(remedial_cost), type_=(FORECAST, VARIABLE), lower=0.0
        )

    def set_flexibility_horizon(self, flexibility_horizon):
        """
        Set the decision horizon, in years, smoothing the flexibility-cost belief.

        It enters the expected policy expenses of the policed vessels.

        A longer horizon makes the belief respond more slowly to changes in the
        flexibility cost between outer time-steps, preventing small changes in future
        fuel availability from translating into expectations of large flexibility-cost
        differences.

        Examples
        --------
        - 3.0
        - Forecast("name")

        Parameters
        ----------
        flexibility_horizon : float | Node
            Decision horizon for the flexibility cost belief, in years.
        """
        self.flexibility_horizon = assign_value(
            as_scalar(flexibility_horizon), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_vessel_threshold(self, vessel_name, threshold):
        """
        Set the threshold that a specific vessel must satisfy in the measure unit.

        If 'ABSOLUTE' the threshold is on absolute emissions in tons/year. If
        'INTENSITY' the threshold is on emission intensity in g/MJ. If 'TRANSPORT' the
        threshold is on carbon intensity index in gCO2-eq/actual cargo-miles. If
        'TRANSPORT_NOMINAL' the threshold is on carbon intensity index in
        gCO2-eq/nominal cargo-miles.

        Every vessel included in the regulation must have a threshold; use the wildcard
        "*" to assign the same threshold to all vessels. If 'Scheme' is 'FLEXIBLE' the
        per-vessel thresholds pool into a single fleet-level constraint.

        Examples
        --------
        - "name", 1e3
        - "*", Forecast("forecast_name")

        Parameters
        ----------
        vessel_name : str
            Name of vessel for which the threshold is assigned.
        threshold : float | Node
            Threshold for a vessel.
        """
        command_assignment_to_dict(
            vessel_name,
            as_scalar(threshold),
            self.vessel_threshold,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

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
        capacity : float | Node
            Capacity of a vessel.
        """
        command_assignment_to_dict(
            vessel_name,
            as_scalar(capacity),
            self.vessel_capacity,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_allow_threshold_adjustment(self, allow_threshold_adjustment):
        """
        Set whether the threshold is automatically adjusted on non-compliance.

        If enabled, the bunker algorithm will perform a multi-step solve where it first
        solves normally, then adjusts the threshold to match achievable compliance
        levels, and re-solves with the adjusted thresholds.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        allow_threshold_adjustment : str
            Whether to allow threshold adjustment (TRUE/FALSE).
        """
        self.allow_threshold_adjustment = assign_boolean(allow_threshold_adjustment)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:
        super().check_requirements()

        if self._scheme is None:
            no_value_assigned_error(self, "Scheme")

        if self._measure is None:
            no_value_assigned_error(self, "Measure")

    def check_consistency(self) -> None:
        super().check_consistency()

        for vessel_name, include_vessel in self.include_vessel.items():
            if include_vessel and (self.vessel_threshold[vessel_name] is None):
                raise ValueError(
                    f'{self}: Vessel("{vessel_name}") is included in the regulation but'
                    " no vessel_threshold is defined."
                )

    def initialize_dependencies(self, vessels):
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        vessels : dict[str, Vessel]
            All vessels in the simulation.
        """
        for vessel_name in vessels:
            self.vessel_threshold.setdefault(vessel_name, None)
            self.vessel_capacity.setdefault(vessel_name, None)

        self._initialize_policy_dependencies(vessels)

    def initialize_expectation(self, length: int, vessels: dict[str, Vessel]) -> None:
        self.expectation.initialize(length, [e.name for e in self.emissions], vessels)

    def initialize_profile(
        self, timeline: np.ndarray, vessels: dict[str, Vessel]
    ) -> None:
        self.profile.initialize(timeline, vessels)

    def calculate_expectation(
        self, emissions, vessels, emissions_lifetime, timeline, idx
    ):

        if not self.active:
            return

        times = timeline[idx:]

        self.expectation.set_remedial_cost(idx, self.remedial_cost.get(times))

        if self.measure in (
            RegulationMeasureID.TRANSPORT,
            RegulationMeasureID.TRANSPORT_NOMINAL,
        ):
            for vessel_name, capacity in self.vessel_capacity.items():
                if capacity is not None:
                    self.expectation.set_vessel_capacity(
                        idx, vessel_name, capacity.get(times)
                    )

                else:
                    nominal_capacity = vessels[vessel_name].nominal_capacity.get(times)
                    self.expectation.set_vessel_capacity(
                        idx, vessel_name, nominal_capacity
                    )

        self._calculate_policy_expectations(
            self.expectation, emissions, emissions_lifetime
        )

    def calculate_profile(self, idx):

        if not self.active:
            return

        self.profile.set_remedial_cost(idx, self.remedial_cost.get())

        for vessel_name, threshold in self.vessel_threshold.items():
            if self.vessel_is_policed(vessel_name):
                self.profile.set_vessel_threshold(idx, vessel_name, threshold.get())

    @property
    def measure(self) -> RegulationMeasureID:
        if self._measure is None:
            no_value_assigned_error(self, "Measure")

        return self._measure
