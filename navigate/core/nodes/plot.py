# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect which plots to render and where.

navigate.output.plots.render.generate_plots renders them from the SimulationResults
of a finished run. The Plot node is not assigned on any other node.
"""

from __future__ import annotations

from navigate.core.node import Node
from navigate.core.node_type import PLOT


class Plot(Node):
    """Hold the plot selection and output directory of a run."""

    def __init__(self, name: str) -> None:
        super().__init__(name, PLOT)

        # external variables -----------------------------------------------------------
        self.directory: str | None = None
        self.selected_plots: set[str] = set()

    # external methods (DSL attributes) ------------------------------------------------
    def set_directory(self, directory: str) -> None:
        """Set the plot output directory."""
        self.directory = directory

    # external methods (DSL commands) --------------------------------------------------
    def add_plot(self, label: str) -> None:
        """Select a plot to render, by its label."""
        self.selected_plots.add(label)
