# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._fuel_base_profile import _FuelBaseProfile

if TYPE_CHECKING:
    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray


class _FuelProducerProfile(_FuelBaseProfile):
    """Base class used exclusively for sub-classing."""

    def __init__(self):
        super().__init__()

        # current production
        self._production_mass: dict[
            str, np.ndarray
        ] = {}  # actual production, tons/year

        # feedstock
        self._feed_mass: dict[
            str, np.ndarray
        ] = {}  # feedstock for production, ton/year

        # constraints
        self._feed_constraint: dict[str, np.ndarray] = {}

    def _initialize_fuel_producer(
        self,
        feedstocks: dict[str, Feedstock],
        fuels: dict[str, Fuel],
        processes: dict[str, Process],
    ) -> None:

        self._production_mass = self._default_dict(fuels)

        feed = {**feedstocks, **processes}
        self._feed_mass = self._default_dict(feed)
        self._feed_constraint = self._default_dict(feed, default=np.inf)

    def add_fuel_producer_profile(
        self, profile: _FuelProducerProfile, idx: int | slice = np.s_[:]
    ) -> None:
        """
        Add another fuel producer profile's values into this one.

        Parameters
        ----------
        profile : _PlantAggregateProfile | ProducerProfile
            Aggregate profile from other node.
        idx : int
            Time-step index.
        """
        for key in self._production_mass:
            self._production_mass[key][idx] += profile._production_mass[key][idx]

        for key in self._feed_mass:
            self._feed_mass[key][idx] += profile._feed_mass[key][idx]

        for key in self._feed_constraint:
            self._feed_constraint[key][idx] += profile._feed_constraint[key][idx]

    def add_production_mass(
        self, fuel_name: str, mass: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._production_mass[fuel_name][idx] += mass

    def add_feed_mass(
        self, feed_name: str, mass: float, idx: int | slice = np.s_[:]
    ) -> None:
        self._feed_mass[feed_name][idx] += mass

    def set_feed_constraint(self, idx: int, feed_name: str, constraint: float) -> None:
        self._feed_constraint[feed_name][idx] = constraint

    def get_production_energy(self) -> dict[str, FloatArray]:
        return self._fuel_mass_to_energy(self._production_mass)

    def get_production_type_energy(self) -> dict[FuelTypeID, FloatArray]:
        return self._fuel_type_mass_to_energy(self._production_mass)

    def get_feed_mass(self) -> dict[str, FloatArray]:
        return dict(self._feed_mass)

    def get_feed_constraint(self) -> dict[str, FloatArray]:
        return dict(self._feed_constraint)
