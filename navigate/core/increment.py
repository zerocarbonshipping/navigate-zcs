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
    cohort's age is read off the current time rather than kept. Its assets are spread
    uniformly over the ages they hold, from the youngest to the oldest; removing the
    oldest of them shortens the age span.

    Parameters
    ----------
    count
        Number of assets in the cohort.
    entered
        Time the cohort's youngest asset entered service; its assets entered
        uniformly over the age span before it.
    age_span
        Width in years of the ages the cohort's assets hold.
    origin
        Time-step index whose attributes the cohort carries.
    """

    count: float
    entered: float
    age_span: float
    origin: int

    def youngest_age(self, time: float) -> float:
        """Return the age of the cohort's youngest asset at a time, in years."""
        return time - self.entered

    def oldest_age(self, time: float) -> float:
        """Return the age of the cohort's oldest asset at a time, in years."""
        return self.youngest_age(time) + self.age_span

    def mean_age(self, time: float) -> float:
        """Return the mean age of the cohort's assets at a time, in years."""
        return self.youngest_age(time) + 0.5 * self.age_span


@dataclass(slots=True)
class VesselIncrement(Increment):
    """
    One cohort of vessels, with the technology it carries.

    Its origin is the time step it was built at, the first for the initial fleet.
    Cohorts copied from one share its package uptake, so a change to the uptake
    replaces the array rather than writing into it.

    Parameters
    ----------
    count
        Number of vessels in the cohort.
    entered
        Time the cohort's youngest vessel entered service.
    age_span
        Width in years of the ages the cohort's vessels hold.
    origin
        Time-step index whose vessel attributes the cohort carries.
    package_uptake
        Share of the cohort on each technology package, one entry per package.
    technology_charter_rate
        Levelized technology cost carried by the cohort, currency/year/vessel.
    """

    package_uptake: FloatArray
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
        Width in years of the ages the cohort's plants hold.
    origin
        Time-step index whose plant attributes the cohort carries.
    decided
        Time the cohort was decided.
    """

    decided: float
