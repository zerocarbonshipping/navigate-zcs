# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The asset cohorts held by the Fleet (vessels) and Producer (plants) nodes.

The fleet and fuel domains build them; navigate.simulation.cohort holds the
accounting the two share.
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

    Its times are on the simulation timeline, in years since the start, so the
    cohort's age is read off the current time rather than kept.

    Parameters
    ----------
    count
        Number of assets in the cohort.
    entered
        Time the cohort's youngest asset entered service; its assets entered
        uniformly over the age span before it.
    age_span
        Width in years of the age bin the cohort spans.
    origin
        Time-step index whose attributes the cohort carries.
    """

    count: float
    entered: float
    age_span: float
    origin: int

    def age(self, time: float) -> float:
        """Return the age of the cohort's youngest asset at a time, in years."""
        return time - self.entered


@dataclass(slots=True)
class VesselIncrement(Increment):
    """
    One cohort of vessels, with the technology it carries.

    Its origin is the time step it was built at, the first for the initial fleet.

    Parameters
    ----------
    count
        Number of vessels in the cohort.
    entered
        Time the cohort's youngest vessel entered service.
    age_span
        Width in years of the age bin the cohort spans.
    origin
        Time-step index whose vessel attributes the cohort carries.
    package_uptake
        Share of the cohort on each technology package, one entry per package.
    scrapped_past_lifetime
        Vessels scrapped from the cohort's part past the vessel lifetime; with the
        count, the cohort's size before that scrapping.
    technology_charter_rate
        Levelized technology cost carried by the cohort, currency/year/vessel.
    """

    package_uptake: FloatArray
    scrapped_past_lifetime: float = 0.0
    technology_charter_rate: float = 0.0


@dataclass(slots=True)
class PlantIncrement(Increment):
    """
    One cohort of plants, with the time it was decided.

    Its origin is the time step nearest its decision.

    Parameters
    ----------
    count
        Number of plants in the cohort.
    entered
        Time the cohort's last plant is delivered, in the future while it is still
        in the pipeline.
    age_span
        Width in years of the age bin the cohort spans.
    origin
        Time-step index whose plant attributes the cohort carries.
    decided
        Time the cohort was decided.
    """

    decided: float
