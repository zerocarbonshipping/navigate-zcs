# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The asset increment data container. The AssetManager node stores one list of increments per asset
type and owns the shared logic that initializes and ages them.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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
