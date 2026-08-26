# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID, RegulationSchemeID
from navigate.util import divide_nonzero


def transfer_regulation_measure(alg: BunkerAlgorithm, properties: dict) -> None:
    """
    Transfer regulation compliance measures.

    Parameters
    ----------
    alg
        The algorithm instance.
    properties
        Pre-computed regulation emission properties.
    """

    for r, regulation in alg.regulations.items():

        if not regulation.is_active():
            continue

        total_emissions = 0.
        total_measure = 0.
        total_rhs = 0.

        for vessel, multiplier in zip(alg.vessels.values(), alg.multipliers.values()):

            v = vessel.get_name()

            if not regulation.vessel_is_policed(v):
                continue

            vessel_emissions, vessel_measure, vessel_rhs = properties[(r, v)]

            total_emissions += multiplier * vessel_emissions
            total_measure += multiplier * vessel_measure
            total_rhs += multiplier * vessel_rhs

            # if the vessel has no ports overlapping with the
            # regulation then the measure is zero and thus ignored
            if not (vessel_measure > 0.):
                continue

            if alg.scope == BunkerScopeID.EXISTING:

                regulation.profile.set_vessel_compliance(alg.idx, v, vessel_emissions / vessel_measure)
                regulation.profile.set_vessel_allowance(alg.idx, v, vessel_rhs)
                regulation.profile.set_vessel_units(alg.idx, v, vessel_emissions)

        if alg.scope == BunkerScopeID.EXISTING:

            # set allowed and achieved units
            regulation.profile.set_shared_allowance(alg.idx, total_rhs)
            regulation.profile.set_shared_units(alg.idx, total_emissions)

            # shared compliance and threshold only make sense for absolute
            # emissions and energy intensity since transport based intensity
            # is not guaranteed to have the same unit
            if regulation.measure in (RegulationMeasureID.ABSOLUTE, RegulationMeasureID.INTENSITY):
                regulation.profile.set_shared_compliance(
                    alg.idx, _normalize_by_measure(regulation.measure, total_emissions, total_measure))

                # the fleet-level effective target of a flexible regulation:
                # the measure-weighted mean of the per-vessel thresholds
                # (equal to the uniform value when thresholds are assigned
                # via a wildcard)
                if regulation.scheme == RegulationSchemeID.FLEXIBLE:
                    regulation.profile.set_shared_threshold(
                        alg.idx, _normalize_by_measure(regulation.measure, total_rhs, total_measure))


def _normalize_by_measure(measure: RegulationMeasureID, value: float, total_measure: float) -> float:
    """Normalize a fleet aggregate by the pooled measure; ABSOLUTE values pass through."""

    if measure == RegulationMeasureID.ABSOLUTE:
        return value

    # division by zero occurs if no vessels are policed
    return divide_nonzero(value, total_measure)
