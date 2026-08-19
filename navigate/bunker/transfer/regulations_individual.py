# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID
from navigate.core.unit import TON_TO_KG


def transfer_regulations_individual(alg: BunkerAlgorithm) -> None:
    """
    Transfer individual regulation remedial factors.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    # transfer regulation solution
    for (r, v), remedial_factor in alg.remedial_factor_individual.items():

        regulation = alg.regulations[r]
        vessel = alg.vessels[v]

        if not regulation.vessel_is_policed(v):
            continue

        # calculate the remedial units across all vessels
        remedial_units = remedial_factor.X * alg.multipliers[v]

        # calculate the remedial revenue and
        # individual vessel contribution
        remedial_expenses = (remedial_factor.Obj / alg.multipliers[v]) * remedial_units
        vessel_remediation = remedial_expenses / alg.multipliers[v]

        if alg.scope == BunkerScopeID.EXISTING:

            # transfer to regulation
            regulation.profile.add_remedial_units(alg.idx, remedial_units)
            regulation.profile.add_remedial_expenses(alg.idx, remedial_expenses)

            # transfer to vessel (remedial_factor.X is per-ship remedial units)
            vessel.profile.add_remedial_units(r, alg.idx, remedial_factor.X)
            vessel.profile.add_remedial_expenses(alg.idx, vessel_remediation)

            # compute and store offset threshold cap in emission tons
            _transfer_max_offset_rhs(alg, regulation, r, v)

        else:

            vessel.expectation.add_policy_expenses(alg.idx, vessel_remediation)

        # transfer adjusted thresholds if threshold adjustment is enabled
        if (alg.scope == BunkerScopeID.EXISTING and regulation.allow_threshold_adjustment
                and (r, v) in alg.adjusted_vessel_thresholds):
            regulation.profile.set_adjusted_vessel_threshold(alg.idx, v, alg.adjusted_vessel_thresholds[(r, v)])


def _transfer_max_offset_rhs(alg: BunkerAlgorithm, regulation, r: str, v: str) -> None:
    """Compute and store the maximum offsettable emission tons for a vessel."""

    if not alg.offsetting_enabled or not regulation.allow_offsetting:
        return

    offset_threshold_attr = regulation.get_effective_offset_threshold()
    if offset_threshold_attr is None:
        return

    offset_threshold_value = offset_threshold_attr.get()
    emissions = alg.regulation_emission_terms[(r, v)].getValue()
    measure = regulation.measure

    if measure == RegulationMeasureID.ABSOLUTE:
        max_offset_tons = max(emissions - offset_threshold_value, 0.)
    elif measure == RegulationMeasureID.INTENSITY:
        energy = alg.regulation_energy_terms[(r, v)].getValue()
        offset_threshold_tons = offset_threshold_value / TON_TO_KG * energy
        max_offset_tons = max(emissions - offset_threshold_tons, 0.)
    else:
        m = alg.regulation_measure[(r, v)]
        offset_threshold_tons = offset_threshold_value * m
        max_offset_tons = max(emissions - offset_threshold_tons, 0.)

    regulation.profile.set_max_offset_rhs(alg.idx, v, max_offset_tons)
