# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import RegulationSchemeID
from navigate.util import derive_smoothing_alpha, update_belief_path


def update_regulation_flexibility_beliefs(regulations: dict, vessels: dict, timeline: np.ndarray, idx: int) -> None:
    """
    Update the flexibility cost belief of every flexible regulation and apply the expected policy expenses.

    The raw flexibility cost (the shadow price of the regulation threshold flexibility constraint) is
    smoothed via exponential moving average, in place on the regulation expectation's belief array.
    This prevents small changes in future fuel availability from translating into expectations of
    large flexibility-cost differences.

    The expected flexibility expenses of each policed vessel are then applied as the net flexibility
    units (flexibility units minus surplus units, stored raw by the bunker transfer) valued at the
    smoothed cost. Surplus revenue is implicitly valued at the same smoothed cost through the net units.

    Parameters
    ----------
    regulations
        Mapping of regulation name to regulation object.
    vessels
        Mapping of vessel name to vessel object.
    timeline
        Simulation timeline in days.
    idx
        Current outer time-step index.
    """

    for regulation in regulations.values():

        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        flexibility_horizon = regulation.flexibility_horizon.get()
        alpha = derive_smoothing_alpha(idx, flexibility_horizon, timeline)

        expectation = regulation.expectation
        raw_cost = expectation.get_flexibility_cost()
        belief = expectation.get_belief_flexibility_cost()

        update_belief_path(raw_cost, belief, alpha, idx)

        for vessel_name, vessel in vessels.items():

            if not regulation.vessel_is_policed(vessel_name):
                continue

            net_units = expectation.get_vessel_net_flexibility_units(vessel_name)
            vessel.expectation.add_policy_expenses_path(idx, net_units[idx:] * belief[idx:])
