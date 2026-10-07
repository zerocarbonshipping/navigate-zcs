# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the results a finished run hands to output for its reports and figures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.core.profiles.global_profile import GlobalProfile
    from navigate.util.types_ import DateArray


@dataclass(frozen=True, slots=True, eq=False)
class SimulationResults:
    """
    Hold everything a finished run hands to its reports and figures.

    Parameters
    ----------
    dateline
        Dates of the simulation timeline.
    profile
        Model-wide profile.
    nodes
        Nodes of the deck, holding their profiles.
    general_nodes
        General nodes of the deck.
    """

    dateline: DateArray
    profile: GlobalProfile
    nodes: Nodes
    general_nodes: GeneralNodes
