# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the asset cohorts, used by the Fleet (vessels) and Producer (plants) nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(slots=True)
class Increment:
    """
    Represent one cohort of assets that entered service together.

    Parameters
    ----------
    multiplier
        Number of assets in the cohort.
    age
        Age of the cohort in years, negative while it is still undelivered.
    age_span
        Width in years of the age bin the cohort spans.
    """

    multiplier: float
    age: float
    age_span: float


@dataclass(slots=True)
class VesselIncrement(Increment):
    """
    Represent one cohort of vessels, with the technology it carries.

    Parameters
    ----------
    multiplier
        Number of vessels in the cohort.
    age
        Age of the cohort in years.
    age_span
        Width in years of the age bin the cohort spans.
    package_uptake
        Share of the cohort on each technology package, one entry per package.
    baseline
        Reference multiplier for partial age-based scrapping; only the oldest cohort
        of a vessel type can hold one, and None marks a cohort that does not.
    technology_charter_rate
        Levelized technology cost carried by the cohort, USD/year/vessel.
    """

    package_uptake: FloatArray
    baseline: float | None = None
    technology_charter_rate: float = 0.0


@dataclass(slots=True)
class PlantIncrement(Increment):
    """
    Represent one cohort of plants, with the time since it was decided.

    Parameters
    ----------
    multiplier
        Number of plants in the cohort.
    age
        Age of the cohort in years, negative while it is still in the pipeline.
    age_span
        Width in years of the age bin the cohort spans.
    decided
        Years since the cohort was decided.
    """

    decided: float
