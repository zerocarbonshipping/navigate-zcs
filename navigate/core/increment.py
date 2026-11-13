# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The asset cohorts held by the Fleet (vessels) and Producer (plants) nodes.

The fleet and fuel domains build and age them; navigate.simulation.cohort holds
the accounting the two share.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray


@dataclass(slots=True)
class Increment:
    """
    One cohort of assets that entered service together.

    Parameters
    ----------
    count
        Number of assets in the cohort.
    age
        Age of the cohort in years.
    age_span
        Width in years of the age bin the cohort spans.
    """

    count: float
    age: float
    age_span: float


@dataclass(slots=True)
class VesselIncrement(Increment):
    """
    One cohort of vessels, with the technology it carries.

    Parameters
    ----------
    count
        Number of vessels in the cohort.
    age
        Age of the cohort in years.
    age_span
        Width in years of the age bin the cohort spans.
    package_uptake
        Share of the cohort on each technology package, one entry per package.
    scrapped_past_lifetime
        Vessels scrapped from the cohort's part past the vessel lifetime; with the
        count, the cohort's size before that scrapping.
    technology_charter_rate
        Levelized technology cost carried by the cohort, USD/year/vessel.
    """

    package_uptake: FloatArray
    scrapped_past_lifetime: float = 0.0
    technology_charter_rate: float = 0.0


@dataclass(slots=True)
class PlantIncrement(Increment):
    """
    One cohort of plants, with the time since it was decided.

    Parameters
    ----------
    count
        Number of plants in the cohort.
    age
        Age of the cohort in years, negative while it is still in the pipeline.
    age_span
        Width in years of the age bin the cohort spans.
    decided
        Years since the cohort was decided.
    """

    decided: float
