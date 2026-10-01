# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Split the units and expenses of FLEXIBLE-scheme regulations between vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import BunkerScopeID
from navigate.util import divide_nonzero

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.bunker.transfer.regulation_properties import RegulationProperties


def transfer_regulation_flexibility(
    alg: BunkerAlgorithm, properties: RegulationProperties
) -> None:
    """
    Split the cost of purchasing flexibility units and selling surplus units.

    A heuristic allocates the amounts between the policed vessels.

    Parameters
    ----------
    alg
        The algorithm instance.
    properties
        Emissions, measure and allowance of each (regulation, vessel) pair.
    """
    for r, remedial_factor in alg.remedial_factor_flexibility.items():
        regulation = alg.regulations[r]

        total_remedial_units = remedial_factor.X
        remedial_cost = regulation.expectation.get_remedial_cost(alg.idx)
        total_remedial_expenses = total_remedial_units * remedial_cost

        # per vessel, the units short of (non-compliance) or beyond (surplus) its
        # allowance
        non_compliance_units = {}
        surplus_units = {}
        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            vessel_emissions, _, vessel_rhs = properties[(r, v)]

            non_compliance_units[v] = max(vessel_emissions - vessel_rhs, 0.0)
            surplus_units[v] = max(vessel_rhs - vessel_emissions, 0.0)

        total_non_compliance_units = sum(
            unit * alg.multipliers[v] for v, unit in non_compliance_units.items()
        )
        total_surplus_units = sum(
            unit * alg.multipliers[v] for v, unit in surplus_units.items()
        )

        # the non-compliance not remediated is covered by flexibility units
        total_flexibility_units = total_non_compliance_units - total_remedial_units

        # the fraction of non-compliance remediated through remedial units rather
        # than surplus units, capped at one against the numerical instability of
        # vessels with a low multiplier (the jump-start fraction)
        remedial_scaling = min(
            1.0,
            np.float64(
                divide_nonzero(
                    total_remedial_units, total_non_compliance_units, default=1.0
                )
            ),
        )

        # the flexibility units are distributed by equal fraction to all vessels
        # with non-compliance
        remedial_units = {}
        flexibility_units = {}
        for v in non_compliance_units:
            remedial_units[v] = non_compliance_units[v] * remedial_scaling
            flexibility_units[v] = non_compliance_units[v] * (1.0 - remedial_scaling)

        # the flexibility units and surplus units may be at a disequilibrium if the
        # surplus-generating fuels are so cheap (e.g., due to subsidies) that they
        # are a good business case regardless of the remuneration from selling them,
        # seen as over-compliance with the global regulation target; the scaling
        # requires positive flexibility units, which numerical instability can make
        # negative
        flexibility_cost = alg.flexible_unit_cost[r]
        if (
            total_flexibility_units > 0.0
            and total_surplus_units > total_flexibility_units
        ):
            # reduce the value of surplus units and the cost of flexibility units
            # linearly, from the threshold down to the zero line, ignoring the
            # option of negative emissions
            scaling = np.float64(
                divide_nonzero(
                    total_flexibility_units, total_surplus_units, default=1.0
                )
            )
            flexibility_cost = flexibility_cost * scaling

        total_flexibility_expenses = total_flexibility_units * flexibility_cost
        total_surplus_revenue = total_surplus_units * flexibility_cost

        if alg.scope == BunkerScopeID.EXISTING:
            regulation.profile.add_remedial_units(total_remedial_units, alg.idx)
            regulation.profile.add_remedial_expenses(total_remedial_expenses, alg.idx)
            regulation.profile.set_flexibility_cost(alg.idx, flexibility_cost)
            regulation.profile.set_flexibility_units(alg.idx, total_flexibility_units)
            regulation.profile.set_flexibility_expenses(
                alg.idx, total_flexibility_expenses
            )
            regulation.profile.set_surplus_units(alg.idx, total_surplus_units)
            regulation.profile.set_surplus_revenue(alg.idx, total_surplus_revenue)

        else:
            regulation.expectation.set_flexibility_cost(alg.idx, flexibility_cost)

        if (
            alg.scope == BunkerScopeID.EXISTING
            and regulation.allow_threshold_adjustment
            and r in alg.adjusted_shared_thresholds
        ):
            regulation.profile.set_adjusted_shared_threshold(
                alg.idx, alg.adjusted_shared_thresholds[r]
            )

        for v, vessel in alg.vessels.items():
            if not regulation.vessel_is_policed(v):
                continue

            remedial_expenses = remedial_units[v] * remedial_cost

            if alg.scope == BunkerScopeID.EXISTING:
                flexibility_expenses = flexibility_units[v] * flexibility_cost
                surplus_revenue = surplus_units[v] * flexibility_cost

                vessel.profile.add_remedial_units(r, remedial_units[v], alg.idx)
                vessel.profile.add_remedial_expenses(remedial_expenses, alg.idx)
                vessel.profile.add_flexibility_expenses(flexibility_expenses, alg.idx)
                vessel.profile.add_surplus_revenue(surplus_revenue, alg.idx)

            else:
                vessel.expectation.add_policy_expenses(alg.idx, remedial_expenses)

                # the expected flexibility expenses and surplus revenue are not applied
                # with the raw flexibility cost: only the net units are stored, and the
                # signal layer applies the expenses with the smoothed flexibility cost
                # belief
                net_units = flexibility_units[v] - surplus_units[v]
                regulation.expectation.set_vessel_net_flexibility_units(
                    alg.idx, v, net_units
                )

            if (
                alg.scope == BunkerScopeID.EXISTING
                and regulation.allow_threshold_adjustment
                and (r, v) in alg.adjusted_vessel_thresholds
            ):
                regulation.profile.set_adjusted_vessel_threshold(
                    alg.idx, v, alg.adjusted_vessel_thresholds[(r, v)]
                )
