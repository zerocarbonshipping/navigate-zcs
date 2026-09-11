# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The Plot node collects which plots to render and where; the rendering is done by
navigate.output.plots.render.generate_plots, driven by the simulation manager. The Plot
node is not assigned on any other node.
"""

from __future__ import annotations

from navigate.core.node import Node
from navigate.core.node_type import PLOT


class Plot(Node):
    def __init__(self, name):
        super().__init__(name, PLOT)

        # external variables -----------------------------------------------------------
        self.directory = None
        self.selected_plots = set()

    # external methods (DSL attributes) ------------------------------------------------
    def set_directory(self, directory):
        """
        Set the plot output directory.

        Parameters
        ----------
        directory : str
            Relative or absolute path for plot output.
        """
        self.directory = directory

    # external methods (DSL commands) --------------------------------------------------
    def add_plot(self, label):
        self.selected_plots.add(label)
