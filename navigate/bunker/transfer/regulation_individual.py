# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the remedial units and expenses of INDIVIDUAL-scheme regulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_regulation_individual(alg: BunkerAlgorithm) -> None:
    """
    Transfer the remedial units and expenses of INDIVIDUAL-scheme regulations.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for (r, v), remedial_factor in alg.remedial_factor_individual.items():
        regulation = alg.regulations[r]
        vessel = alg.vessels[v]

        if not regulation.vessel_is_policed(v):
            continue

        # the variable holds the units of one vessel; the regulation totals cover all
        # the vessels it represents
        remedial_units = remedial_factor.X * alg.multipliers[v]

        # the objective coefficient carries the multiplier, so dividing it out gives
        # the remedial cost per unit
        remedial_expenses = (remedial_factor.Obj / alg.multipliers[v]) * remedial_units
        vessel_remediation = remedial_expenses / alg.multipliers[v]

        if alg.scope == BunkerScopeID.EXISTING:
            regulation.profile.add_remedial_units(remedial_units, alg.idx)
            regulation.profile.add_remedial_expenses(remedial_expenses, alg.idx)
            vessel.profile.add_remedial_units(r, remedial_factor.X, alg.idx)
            vessel.profile.add_remedial_expenses(vessel_remediation, alg.idx)

        else:
            vessel.expectation.add_policy_expenses(alg.idx, vessel_remediation)

        if (
            alg.scope == BunkerScopeID.EXISTING
            and regulation.allow_threshold_adjustment
            and (r, v) in alg.adjusted_vessel_thresholds
        ):
            regulation.profile.set_adjusted_vessel_threshold(
                alg.idx, v, alg.adjusted_vessel_thresholds[(r, v)]
            )
