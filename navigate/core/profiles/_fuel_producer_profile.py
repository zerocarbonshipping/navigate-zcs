# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer for the fuel producers: producers and the manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._fuel_base_profile import _FuelBaseProfile
from navigate.core.profiles._fuel_type_lookup import _FuelTypeLookup

if TYPE_CHECKING:
    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray


class _FuelProducerProfile(_FuelBaseProfile, _FuelTypeLookup):
    """Fuel produced, feedstock consumed and the availability limit on it."""

    def __init__(self) -> None:
        super().__init__()

        self._production_mass: dict[str, FloatArray] = {}  # produced, tons/year

        self._feed_mass: dict[str, FloatArray] = {}  # feedstock used, ton/year
        self._feed_constraint: dict[str, FloatArray] = {}  # feed available, ton/year

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
        profile
            Producer profile from another node.
        idx
            Time-step index or slice.
        """
        for fuel_name in self._production_mass:
            self._production_mass[fuel_name][idx] += profile._production_mass[
                fuel_name
            ][idx]

        for feed_name in self._feed_mass:
            self._feed_mass[feed_name][idx] += profile._feed_mass[feed_name][idx]

        for feed_name in self._feed_constraint:
            self._feed_constraint[feed_name][idx] += profile._feed_constraint[
                feed_name
            ][idx]

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
