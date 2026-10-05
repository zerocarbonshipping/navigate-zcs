# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The plot data a run hands to the plot renderer, built by SimulationManager.

PlotData is what the plot functions in output/plots/ read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.core.profiles.manager_profile import ManagerProfile
    from navigate.simulation import SimulationManager
    from navigate.util.types_ import DateArray, FloatArray


@dataclass(eq=False, repr=False)
class PlotData:
    """Container that captures all simulation state needed by plot functions."""

    dateline: DateArray
    timeline: FloatArray
    profile: ManagerProfile
    nodes: Nodes
    general_nodes: GeneralNodes
    deck_directory: str

    @classmethod
    def from_manager(cls, manager: SimulationManager) -> PlotData:
        """
        Create a PlotData instance from a completed SimulationManager.

        Parameters
        ----------
        manager
            The manager after simulation has completed.

        Returns
        -------
        PlotData
            A new PlotData instance with references to manager state.
        """
        return cls(
            dateline=manager.dateline,
            timeline=manager.timeline,
            profile=manager.profile,
            nodes=manager.nodes,
            general_nodes=manager.general_nodes,
            deck_directory=manager.deck_directory,
        )
