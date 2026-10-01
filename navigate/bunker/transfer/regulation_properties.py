# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Evaluate each policed vessel's regulated emissions, measure and allowance."""

from __future__ import annotations

from typing import TYPE_CHECKING

import navigate.core.enum_ as enum_
from navigate.bunker.constraints.regulation_terms import get_regulation_vessel_threshold
from navigate.core.enum_ import RegulationMeasureID
from navigate.core.unit import TON_TO_KG

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.regulation import Regulation

type RegulationProperties = dict[tuple[str, str], tuple[float, float, float]]


def _get_adjusted_threshold(
    alg: BunkerAlgorithm, regulation: Regulation, v: str
) -> float | None:
    """
    Return the adjusted threshold of a regulation-vessel pair, or None if unadjusted.

    A FLEXIBLE scheme returns the shared (fleet-average) adjusted threshold, so that
    all vessels are measured against the same target; an INDIVIDUAL scheme returns
    the vessel's own.
    """
    r = regulation.name
    scheme = regulation.scheme
    if (
        scheme == enum_.RegulationSchemeID.FLEXIBLE
        and r in alg.adjusted_shared_thresholds
    ):
        return alg.adjusted_shared_thresholds[r]

    if (
        scheme == enum_.RegulationSchemeID.INDIVIDUAL
        and (r, v) in alg.adjusted_vessel_thresholds
    ):
        return alg.adjusted_vessel_thresholds[(r, v)]

    return None


def calculate_regulation_emission_properties(
    alg: BunkerAlgorithm,
) -> RegulationProperties:
    """
    Evaluate the regulated emissions, measure and allowance of each policed vessel.

    After threshold adjustment the adjusted (achievable) threshold is used, so that
    non-compliance and surplus are measured against the target the fleet actually
    trades against. The flexibility market price (MAC) then distributes the costs
    between the vessels that over-comply and those that under-comply.

    Parameters
    ----------
    alg
        The algorithm instance.

    Returns
    -------
    RegulationProperties
        Emissions, measure and allowance (rhs) of each (regulation, vessel) pair.
    """
    properties = {}

    for r, regulation in alg.regulations.items():
        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            emissions = alg.regulation_emission_terms[(r, v)].getValue()

            if regulation.measure == RegulationMeasureID.INTENSITY:
                # both the emissions and the allowance of an intensity measure are a
                # function of the bunker solution
                vessel_measure = alg.regulation_energy_terms[(r, v)].getValue()
                vessel_measure /= TON_TO_KG

                threshold = _get_adjusted_threshold(alg, regulation, v)
                if threshold is None:
                    threshold = get_regulation_vessel_threshold(alg, regulation, v)

                rhs = threshold * vessel_measure

            else:
                vessel_measure = alg.regulation_measure[(r, v)]

                threshold = _get_adjusted_threshold(alg, regulation, v)
                if threshold is not None:
                    if regulation.measure == RegulationMeasureID.ABSOLUTE:
                        rhs = threshold
                    else:
                        rhs = threshold * vessel_measure

                elif regulation.scheme == enum_.RegulationSchemeID.INDIVIDUAL:
                    rhs = alg.regulation_rhs_individual[(r, v)]

                else:
                    rhs = alg.regulation_rhs_flexibility[(r, v)]

            properties[(r, v)] = (emissions, vessel_measure, rhs)

    return properties
