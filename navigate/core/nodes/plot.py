# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import os

from navigate.core.node import Node
from navigate.core.node_type import PLOT


class Plot(Node):
    def __init__(self, name):
        super().__init__(name)

        self._type = PLOT

        # external properties
        self._directory = None
        self._selected_plots = set()

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_directory(self, directory):
        """
        Set the plot output directory.

        Parameters
        ----------
        directory : str
            Relative or absolute path for plot output.
        """
        self._directory = directory

    # external commands called in the input deck -----------------------------------------------------------------------
    def add_plot(self, label):
        self._selected_plots.add(label)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        pass

    def generate_plots(self, plot_data):
        """
        Generate plots from exported plot data.

        Parameters
        ----------
        plot_data : PlotData
            The plot data container with simulation state.
        """
        from navigate.output.plots.render import render_plots

        deck_directory = plot_data.get_deck_directory()
        directory = os.path.join(deck_directory, self._directory) if self._directory else None
        selected_plots = self._selected_plots or None  # empty set → None → all plots
        render_plots(plot_data, directory=directory, selected_plots=selected_plots)
