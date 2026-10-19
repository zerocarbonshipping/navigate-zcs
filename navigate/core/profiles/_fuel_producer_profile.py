# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The profile layer for the fuel producers: the producer and global profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.profiles._base_profile import _BaseProfile, accumulate, result

if TYPE_CHECKING:
    from navigate.core.enum_ import FuelTypeID
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _FuelProducerProfile(_BaseProfile):
    """Fuel produced, feedstock consumed and the availability limit on it."""

    # the mass is written, the energy computed from it
    production_mass: dict[str, FloatArray] = field(init=False)
    production_energy: dict[str, FloatArray] = result("GJ/year")
    production_type_energy: dict[FuelTypeID, FloatArray] = result("GJ/year")

    feed_mass: dict[str, FloatArray] = result("t/year")
    feed_constraint: dict[str, FloatArray] = result("t/year")

    def _initialize_fuel_producer(
        self,
        feedstocks: dict[str, Feedstock],
        processes: dict[str, Process],
    ) -> None:
        self.production_mass = self._default_dict(self.context.fuels)

        feed = {**feedstocks, **processes}
        self.feed_mass = self._default_dict(feed)
        self.feed_constraint = self._default_dict(feed, default=np.inf)

    def add_fuel_producer_profile(self, profile: _FuelProducerProfile) -> None:
        """
        Add another fuel producer profile's values into this one.

        Parameters
        ----------
        profile
            Producer profile from another node.
        """
        accumulate(self.production_mass, profile.production_mass)
        accumulate(self.feed_mass, profile.feed_mass)
        accumulate(self.feed_constraint, profile.feed_constraint)
