# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID
from navigate.core.unit import TON_TO_KG
from navigate.util import divide_nonzero


def transfer_regulations_flexibility(alg: BunkerAlgorithm, properties: dict) -> None:
    """
    Use a heuristic to split the cost of purchasing flexibility units and selling surplus units between the
    relevant vessels.

    Parameters
    ----------
    alg
        The algorithm instance.
    properties
        Pre-computed regulation emission properties.
    """

    for r, remedial_factor in alg.remedial_factor_flexibility.items():

        regulation = alg.regulations[r]

        # calculate the remedial units and expenses
        total_remedial_units = remedial_factor.X
        remedial_cost = regulation.expectation.get_remedial_cost(alg.idx)
        total_remedial_expenses = total_remedial_units * remedial_cost

        # calculate the flexibility units required
        # or surplus units generated per vessel
        non_compliance_factor = {}
        non_compliance_units = {}
        surplus_factor = {}
        surplus_units = {}
        for v in alg.vessels:

            if not regulation.vessel_is_policed(v):
                continue

            # extract the emitted emissions and the allowed emissions
            E_v, m_v, rhs_v = properties[(r, v)]

            # calculate the units associated with the factors
            non_compliance_units[v] = max(E_v - rhs_v, 0.)
            surplus_units[v] = max(rhs_v - E_v, 0.)

            # calculate the non-compliance and surplus factors
            non_compliance_factor[v] = non_compliance_units[v] / m_v
            surplus_factor[v] = surplus_units[v] / m_v

        total_non_compliance_units = sum(unit * alg.multipliers[v] for v, unit in non_compliance_units.items())
        total_surplus_units = sum(unit * alg.multipliers[v] for v, unit in surplus_units.items())

        # the flexibility units is the difference between
        # the non-compliance units and the remedial units
        total_flexibility_units = total_non_compliance_units - total_remedial_units

        # calculate the fraction of non-compliance that
        # is remediated through the purchase of remedial
        # units rather than surplus unit. Clamping at zero
        # to avoid issues with numerical instability for
        # low multiplier vessels (jump-start fraciton)
        remedial_scaling = min(1., divide_nonzero(total_remedial_units, total_non_compliance_units, default=1.))

        # the flexibility units are distributed by equal
        # fraction to all vessels with non-compliance
        remedial_units = {}
        flexibility_units = {}
        for v in non_compliance_factor:

            remedial_units[v] = non_compliance_units[v] * remedial_scaling
            flexibility_units[v] = non_compliance_units[v] * (1. - remedial_scaling)

        # the flexibility units and surplus units may be at a disequilibrium
        # if the surplus generating fuels are so cheap (e.g., due to subsidies)
        # that they are a good business case regardless of the remuneration from
        # the selling them (this is seen through over compliance with the global
        # regulation target). Ensure flexibility units are non-negative which can
        # happen due to numerical instability leading to negative scaling issues
        flexibility_cost = alg.flexible_unit_cost[r]
        if total_flexibility_units > 0. and total_surplus_units > total_flexibility_units:

            # when offsetting with threshold adjustment is active, the surplus/non-compliance
            # split is an artifact of the adjusted threshold — skip scaling so the flexibility
            # cost reflects the true shadow price (= offset or remedial cost)
            has_offset_adjustment = (regulation.allow_offsetting
                                     and regulation.allow_threshold_adjustment
                                     and alg.offsetting_enabled)

            if not has_offset_adjustment:
                # linearly reduce the value of surplus units/cost of
                # flexible units. The linear scaling happens from the
                # threshold and down to the zero-line thus ignoring
                # the option of negative emissions.
                scaling = divide_nonzero(total_flexibility_units, total_surplus_units, default=1.)
                flexibility_cost = flexibility_cost * scaling

        # calculate the total flexibility expenses and surplus revenue
        total_flexibility_expenses = total_flexibility_units * flexibility_cost
        total_surplus_revenue = total_surplus_units * flexibility_cost

        if alg.scope == BunkerScopeID.EXISTING:

            # transfer remedial
            regulation.profile.add_remedial_units(alg.idx, total_remedial_units)
            regulation.profile.add_remedial_expenses(alg.idx, total_remedial_expenses)

            # transfer flexibility
            regulation.profile.set_flexibility_cost(alg.idx, flexibility_cost)
            regulation.profile.set_flexibility_units(alg.idx, total_flexibility_units)
            regulation.profile.set_flexibility_expenses(alg.idx, total_flexibility_expenses)

            # transfer surplus
            regulation.profile.set_surplus_units(alg.idx, total_surplus_units)
            regulation.profile.set_surplus_revenue(alg.idx, total_surplus_revenue)

        else:
            regulation.expectation.set_flexibility_cost(alg.idx, flexibility_cost)

        # transfer adjusted shared threshold if threshold adjustment is enabled
        if (alg.scope == BunkerScopeID.EXISTING and regulation.allow_threshold_adjustment
                and r in alg.adjusted_shared_thresholds):
            regulation.profile.set_adjusted_shared_threshold(alg.idx, alg.adjusted_shared_thresholds[r])

        # transfer to vessels
        for v, vessel in alg.vessels.items():

            if not regulation.vessel_is_policed(v):
                continue

            # calculate the vessel remedial expenses
            remedial_expenses = remedial_units[v] * remedial_cost

            if alg.scope == BunkerScopeID.EXISTING:

                # calculate the vessel flexibility expenses and surplus revenue
                flexibility_expenses = flexibility_units[v] * flexibility_cost
                surplus_revenue = surplus_units[v] * flexibility_cost

                vessel.profile.add_remedial_units(r, alg.idx, remedial_units[v])
                vessel.profile.add_remedial_expenses(alg.idx, remedial_expenses)
                vessel.profile.add_flexibility_expenses(alg.idx, flexibility_expenses)
                vessel.profile.add_surplus_revenue(alg.idx, surplus_revenue)

                # compute and store offset threshold cap in emission tons
                _transfer_max_offset_rhs(alg, regulation, r, v)

            else:

                vessel.expectation.add_policy_expenses(alg.idx, remedial_expenses)

                # the expected flexibility expenses and surplus revenue are not applied
                # here with the raw flexibility cost. Only the net units are stored;
                # the expenses are applied in the signal layer using the smoothed
                # flexibility cost belief
                net_units = flexibility_units[v] - surplus_units[v]
                regulation.expectation.set_vessel_net_flexibility_units(alg.idx, v, net_units)

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
