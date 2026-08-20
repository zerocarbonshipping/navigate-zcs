# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import (
    Node,
    Scalar,
    as_scalar,
    as_scalar_list,
    assign_list,
    assign_value,
)
from navigate.core.id_ import CURVE, FORECAST, VARIABLE
from navigate.core.misc import YEAR

if TYPE_CHECKING:
    from navigate.core import NodeReference

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Increment:
    """
    A single asset increment representing one cohort of assets
    (vessels or plants) that entered service at the same time.
    """

    multiplier: float
    age: float
    dt: float
    decided: float | None = None
    package_uptake: np.ndarray | None = None  # Fleet: technology package uptake per increment
    baseline: float | None = None  # Fleet: reference multiplier for partial age-based scrapping
    technology_charter_rate: float = 0.  # Fleet: levelized technology cost carried by the cohort, USD/year per vessel


class AssetManager(Node):
    """
    Base class for fleet-like and producer-like asset managers that track
    increments of asset types over time using a discrete-choice investment model.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # shared decision attribute
        self.inertia: Scalar | None = None

        # initial conditions
        self._initial_age_distribution: list = []

        # asset types (vessels or plants)
        self.assets: list = []

        # increment storage — one list of Increment per asset type
        self.increments: list[list[Increment]] = []

        # dynamic properties
        self.current_uptake: np.ndarray = np.empty(0)

    # -- abstract interface that subclasses must provide ----------------------------------

    def _get_initial_multiplier(self, index: int) -> float:
        """Return the total initial multiplier for asset type at *index*."""
        raise NotImplementedError

    # -- shared setter methods (identical in Producer and Fleet) --------------------------

    def set_inertia(self, inertia: float | NodeReference) -> None:
        """
        Set the inertia used in the uptake decision of newbuild assets.

        The inertia is defined as the fraction of newbuilds that must follow the same asset type distribution as the
        previous time-step. It is defined in fraction/year.

        Examples
        --------
        - 0.66
        - Forecast("name")

        Parameters
        ----------
        inertia
            The newbuild asset type inertia.
        """

        self.inertia = assign_value(as_scalar(inertia), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_initial_age_distribution(self, initial_age_distribution) -> None:
        """
        Set the initial age distribution of each asset type.

        The list must have a length corresponding to the number of asset types.
        Each entry is either a Curve reference (where the Curve's x-values are ages in increasing order
        and y-values are the corresponding fractions) or 0 for asset types with no custom distribution.

        Examples
        --------
        - [Curve("age_dist_1"), 0, Curve("age_dist_3")]

        Parameters
        ----------
        initial_age_distribution
            List of Curve references for the age distribution of each asset type.
        """

        self._initial_age_distribution = assign_list(as_scalar_list(initial_age_distribution), type_=CURVE, lower=0.)

    # -- shared increment initialization -------------------------------------------------

    def _define_initial_age(self) -> None:
        """
        Define the age distribution of the existing assets and create
        empty Increment lists with ages and dt populated.
        """

        assets = self.assets

        for a, asset in enumerate(assets):

            increments: list[Increment] = []

            if self._get_initial_multiplier(a) > 0.:

                if self._initial_age_distribution and isinstance(self._initial_age_distribution[a], Node):

                    curve = self._initial_age_distribution[a]
                    ages = curve.get_x()[::-1].copy()

                else:

                    lifetime = asset.lifetime.get()
                    lifetime = self._adjust_lifetime_for_age(lifetime)
                    ages = np.linspace(lifetime - 1., 0., int(lifetime))

                # It is assumed that the first multiplier
                # increment was entered over a year
                dts = np.insert(ages[:-1] - ages[1:], 0, 1.) if ages.size else np.array([], dtype=np.float64)

                for i in range(ages.size):
                    increments.append(Increment(multiplier=0., age=float(ages[i]), dt=float(dts[i])))

            self.increments.append(increments)

    def _adjust_lifetime_for_age(self, lifetime: float) -> float:
        """
        Hook for subclasses to adjust the perceived lifetime used in initial age discretization.
        Fleet overrides this to account for fixed scrap rates.
        """

        return lifetime

    def _define_initial_multipliers(self) -> None:
        """
        Define the initial numbers of assets of each asset type by distributing
        the total multiplier across age-based increments.
        """

        assets = self.assets

        for a in range(len(assets)):

            multiplier = self._get_initial_multiplier(a)
            incs = self.increments[a]
            n = len(incs)

            if multiplier > 0. and n > 0:

                if self._initial_age_distribution and isinstance(self._initial_age_distribution[a], Node):

                    curve = self._initial_age_distribution[a]
                    fractions = curve.get_y()[::-1]

                    for i, inc in enumerate(incs):
                        inc.multiplier = multiplier * fractions[i]

                else:

                    for inc in incs:
                        inc.multiplier = multiplier / n

    # -- shared runtime methods ----------------------------------------------------------

    @staticmethod
    def _age_increments(increment_lists: list[list[Increment]], dt: float) -> None:
        """
        Age every increment in the given lists by *dt* years.

        Parameters
        ----------
        increment_lists
            Nested lists of increments (one list per asset type).
        dt
            Time-step size in years.
        """

        for incs in increment_lists:
            for inc in incs:
                inc.age += dt
                if inc.decided is not None:
                    inc.decided += dt

    def update_increment_ages(self, time_step: float) -> None:
        """
        Update the ages of all active increments with the progressed time since last time-step.

        Parameters
        ----------
        time_step
            Current time-step size.
        """

        self._age_increments(self.increments, time_step / YEAR)

    def get_multiplier(self, index: int) -> float:
        return sum(inc.multiplier for inc in self.increments[index])

    def get_multipliers(self) -> list[float]:
        return [self.get_multiplier(a) for a in range(len(self.increments))]
