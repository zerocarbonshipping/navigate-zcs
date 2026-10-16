# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Copy the per-time-step regulation spend coefficients into the LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_regulation_spend_coefficients(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    """
    Copy a vessel's regulation spend coefficients at the evaluated step into the LP.

    The LP keeps its own copies, as threshold adjustment rewrites them between
    solves. Shore power is copied only at the ports where the vessel already has a
    shore-power variable.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose coefficients are copied.
    """
    v = vessel.name
    idx = alg.idx

    for r, regulation in alg.active_regulations.items():
        expectation = regulation.expectation

        for c, burned in vessel.fuels_per_converter.items():
            for f in burned:
                coefficient = expectation.get_spend_coefficient((v, c, f), idx)
                alg.regulation_spend_coefficient[(v, c, f, r)] = coefficient

        for p, port in enumerate(vessel.route.ports):
            if (v, p) not in alg.shore_power:
                continue

            key = (v, port.name)
            coefficient = expectation.get_shore_power_spend_coefficient(key, idx)
            alg.shore_power_regulation_coefficient[(v, p, r)] = coefficient
