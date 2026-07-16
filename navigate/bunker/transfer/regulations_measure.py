# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.core.enum_ import BunkerScopeID, RegulationMeasureID
from navigate.util import divide_nonzero


def transfer_regulations_measure(alg: BunkerAlgorithm, properties: dict) -> None:
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

        E = 0.
        m = 0.
        rhs = 0.

        for vessel, multiplier in zip(alg.vessels.values(), alg.multipliers.values()):

            v = vessel.get_name()

            if not regulation.vessel_is_policed(v):
                continue

            E_v, m_v, rhs_v = properties[(r, v)]

            E += multiplier * E_v
            m += multiplier * m_v
            rhs += multiplier * rhs_v

            # if the vessel has no ports overlapping with the
            # regulation then the measure is zero and thus ignored
            if not (m_v > 0.):
                continue

            if alg.scope == BunkerScopeID.EXISTING:

                regulation.profile.set_vessel_compliance(alg.idx, v, E_v / m_v)
                regulation.profile.set_vessel_allowance(alg.idx, v, rhs_v)
                regulation.profile.set_vessel_units(alg.idx, v, E_v)

        if regulation.measure == RegulationMeasureID.ABSOLUTE:
            shared_compliance = E
        else:
            # division by zero occurs if no vessels are policed
            shared_compliance = divide_nonzero(E, m)

        if alg.scope == BunkerScopeID.EXISTING:

            # set allowed and achieved units
            regulation.profile.set_shared_allowance(alg.idx, rhs)
            regulation.profile.set_shared_units(alg.idx, E)

            # shared compliance only makes sense for absolute emissions
            # and energy intensity since transport based intensity is
            # not guaranteed to have the same unit
            if regulation.measure in (RegulationMeasureID.ABSOLUTE, RegulationMeasureID.INTENSITY):
                regulation.profile.set_shared_compliance(alg.idx, shared_compliance)
