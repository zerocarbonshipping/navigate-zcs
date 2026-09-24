# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the asset increment container, used across the fleet and fuel domains."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(slots=True)
class Increment:
    """
    Represent one cohort of assets, vessels or plants, that entered service together.

    Parameters
    ----------
    multiplier
        Number of assets in the cohort.
    age
        Age of the cohort in years, negative while it is still undelivered.
    dt
        Width in years of the age bin the cohort spans.
    decided
        Years since the cohort was decided, None until it is assigned.
    package_uptake
        Share of the cohort on each technology package; fleet only.
    baseline
        Reference multiplier for partial age-based scrapping; fleet only.
    technology_charter_rate
        Levelized technology cost carried by the cohort, USD/year/vessel; fleet only.
    """

    multiplier: float  # number of assets in the cohort
    age: float  # age of the cohort, years
    dt: float  # width of the age bin the cohort spans, years
    decided: float | None = None  # years since the cohort was decided
    package_uptake: FloatArray | None = None  # cohort share per package, fleet only
    baseline: float | None = None  # reference multiplier for scrapping, fleet only
    technology_charter_rate: float = 0.0  # levelized cost, USD/year/vessel, fleet only
