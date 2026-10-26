# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results layer for the fuel producers: the producer and global results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.results._base_results import _BaseResults, accumulate, result

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.enum_ import FuelTypeID
    from navigate.util.types_ import FloatArray


@dataclass(eq=False, repr=False)
class _FuelProducerResults(_BaseResults):
    """Fuel produced, and feed used and available per feedstock and process."""

    # the mass is written, the energy computed from it
    production_mass: dict[str, FloatArray] = field(init=False)
    production_energy: dict[str, FloatArray] = result("GJ/year")
    production_type_energy: dict[FuelTypeID, FloatArray] = result("GJ/year")

    feed_mass: dict[str, FloatArray] = result("t/year")
    feed_constraint: dict[str, FloatArray] = result("t/year")

    def _initialize_fuel_producer(
        self, feedstock_names: Sequence[str], process_names: Sequence[str]
    ) -> None:
        self.production_mass = self._default_dict(self.context.fuels)

        feed_names = [*feedstock_names, *process_names]
        self.feed_mass = self._default_dict(feed_names)
        self.feed_constraint = self._default_dict(feed_names, default=np.inf)

    def add_fuel_producer_results(self, results: _FuelProducerResults) -> None:
        """
        Add another fuel producer's results into this one.

        Parameters
        ----------
        results
            Producer results from another node.
        """
        accumulate(self.production_mass, results.production_mass)

        accumulate(self.feed_mass, results.feed_mass)
        accumulate(self.feed_constraint, results.feed_constraint)
