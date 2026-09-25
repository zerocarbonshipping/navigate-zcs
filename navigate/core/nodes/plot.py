# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect which plots to render and where.

The rendering itself is done by navigate.output.plots.render.generate_plots, driven
by the simulation manager. The Plot node is not assigned on any other node.
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
        """
        Set the plot output directory.

        Parameters
        ----------
        directory
            Relative or absolute path for plot output.
        """
        self.directory = directory

    # external methods (DSL commands) --------------------------------------------------
    def add_plot(self, label: str) -> None:
        """
        Select a plot to render, by its label.

        Call once per plot; every available plot is rendered when no 'add_plot'
        command is given at all.

        Examples
        --------
        - "global_fuel_consumed"

        Parameters
        ----------
        label
            Plot label, one of the labels listed in the reference manual.
        """
        self.selected_plots.add(label)
