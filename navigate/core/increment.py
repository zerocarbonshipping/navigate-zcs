# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Define the asset increment data container.

The _AssetManager node stores one list of increments per asset type and owns the
shared logic that initializes and ages them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass(slots=True)
class Increment:
    """
    Represent one cohort of assets that entered service at the same time.

    Assets are vessels or plants.
    """

    multiplier: float
    age: float
    dt: float
    decided: float | None = None
    package_uptake: np.ndarray | None = (
        None  # Fleet: technology package uptake per increment
    )
    baseline: float | None = (
        None  # Fleet: reference multiplier for partial age-based scrapping
    )
    technology_charter_rate: float = (
        0.0  # Fleet: levelized technology cost carried by the cohort, USD/year/vessel
    )
