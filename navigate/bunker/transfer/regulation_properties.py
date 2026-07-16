# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

import navigate.core.enum_ as enum_
from navigate.bunker.constraints.regulation_helpers import get_regulation_vessel_threshold
from navigate.core.enum_ import RegulationMeasureID
from navigate.core.unit import TON_TO_KG


def _get_adjusted_threshold(alg: BunkerAlgorithm, regulation, r: str, v: str) -> float | None:
    """Return the adjusted threshold for a regulation-vessel pair, or None if unadjusted.

    For FLEXIBLE schemes the shared (fleet-average) adjusted threshold is
    returned so that all vessels are measured against the same target.
    For INDIVIDUAL schemes the per-vessel adjusted threshold is returned.
    """
    scheme = regulation.scheme
    if scheme == enum_.RegulationSchemeID.FLEXIBLE and r in alg.adjusted_shared_thresholds:
        return alg.adjusted_shared_thresholds[r]
    if scheme == enum_.RegulationSchemeID.INDIVIDUAL and (r, v) in alg.adjusted_vessel_thresholds:
        return alg.adjusted_vessel_thresholds[(r, v)]
    return None


def calculate_regulation_emission_properties(alg: BunkerAlgorithm) -> dict:
    """
    Calculates the emissions and the allowed emissions for a given regulation and ship/vessel.

    After threshold adjustment the adjusted (achievable) threshold is used so that
    non-compliance and surplus are measured against the target the fleet actually
    trades against.  The flexibility market price (MAC) then correctly distributes
    costs between vessels that over-comply and those that under-comply.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    dict
        Dict mapping (r, v) to (emissions, measure, rhs).
    """

    properties = {}

    for r, regulation in alg.regulations.items():

        for v in alg.vessels:

            if not regulation.vessel_is_policed(v):
                continue

            emissions = alg.regulation_emission_terms[(r, v)].getValue()

            # calculate the emitted emissions and the allowed emissions
            if regulation.measure == RegulationMeasureID.INTENSITY:

                # intensity is a special case because both the emissions
                # and allowance are a function of the bunker solution
                measure = alg.regulation_energy_terms[(r, v)].getValue()
                measure /= TON_TO_KG

                threshold = _get_adjusted_threshold(alg, regulation, r, v)
                if threshold is None:
                    threshold = get_regulation_vessel_threshold(alg, regulation, v)

                rhs = threshold * measure

            else:

                measure = alg.regulation_measure[(r, v)]

                threshold = _get_adjusted_threshold(alg, regulation, r, v)
                if threshold is not None:

                    if regulation.measure == RegulationMeasureID.ABSOLUTE:
                        rhs = threshold
                    else:
                        rhs = threshold * measure

                elif regulation.scheme == enum_.RegulationSchemeID.INDIVIDUAL:
                    rhs = alg.regulation_rhs_individual[(r, v)]

                else:
                    rhs = alg.regulation_rhs_flexibility[(r, v)]

            # bundle output
            properties[(r, v)] = (emissions, measure, rhs)

    return properties
