# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Define _AssetManager, the base class of the Fleet and Producer nodes.

It is never assigned or instantiated directly through the DSL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar, as_list, as_scalar, assign_list, assign_value
from navigate.core.node import Node
from navigate.core.node_type import CURVE, FORECAST, VARIABLE
from navigate.core.nodes.curve import Curve

if TYPE_CHECKING:
    from navigate.core.increment import Increment
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import ForecastArgument, ForecastInput
    from navigate.util.types_ import FloatArray


class _AssetManager[A: Vessel | Plant, I: Increment](Node):
    """Track asset-type increments via a discrete-choice investment model."""

    def __init__(self, name: str, type_: str) -> None:
        super().__init__(name, type_)

        # external variables -----------------------------------------------------------
        # shared decision attribute
        self.inertia: ForecastInput = Scalar(0.0)

        # initial conditions
        self.initial_age_distribution: list[Scalar | Curve] = []

        # asset types (vessels or plants)
        self.assets: list[A]

        # internal variables -----------------------------------------------------------
        self.increments: list[list[I]] = []

        self.current_uptake: FloatArray = np.empty(0)

    # external methods (DSL attributes) ------------------------------------------------
    def set_inertia(self, inertia: ForecastArgument) -> None:
        """Set the inertia used in the uptake decision of newbuild assets."""
        self.inertia = assign_value(
            as_scalar(inertia), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
        )

    def set_initial_age_distribution(
        self,
        initial_age_distribution: (float | Curve | list[float | Curve]),
    ) -> None:
        """Set the initial age distribution of each asset type."""
        entries: list[float | Curve] = as_list(initial_age_distribution)
        self.initial_age_distribution = assign_list(
            [as_scalar(entry) for entry in entries],
            type_=CURVE,
            lower=0.0,
            allow_expression=False,
        )

    # internal methods -----------------------------------------------------------------
    def _check_initial_age_distribution_is_finite(self) -> None:
        """Reject an initial age distribution holding an INF or -INF fraction."""
        # its Curves are read as tables, never evaluated, so no bound they are
        # assigned under ever checks their fractions; the table itself rejects
        # a non-finite age
        for distribution in self.initial_age_distribution:
            if not isinstance(distribution, Curve):
                continue

            if not np.all(np.isfinite(distribution.y)):
                raise ValueError(
                    f"{self}: InitialAgeDistribution ({distribution}) must hold "
                    "finite values."
                )
