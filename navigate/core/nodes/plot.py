# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Define the Plot node, the plots a run renders and where.

navigate.output.plots.render.generate_plots renders them from the SimulationResults
of a finished run. The Plot node is not assigned on any other node.
"""

from __future__ import annotations

from navigate.core import SECTION_DEFINE, deck_attribute, deck_command
from navigate.core.node import Node
from navigate.core.node_type import PLOT


class Plot(Node):
    """A plot selection: the plots a run renders and the directory they go to."""

    type = PLOT

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.directory: str | None = None
        self.selected_plots: set[str] = set()

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE)
    def set_directory(self, directory: str) -> None:
        """Set the plot output directory."""
        self.directory = directory

    # external methods (DSL commands) --------------------------------------------------
    @deck_command(SECTION_DEFINE)
    def add_plot(self, label: str) -> None:
        """Select a plot to render, by its label."""
        self.selected_plots.add(label)
