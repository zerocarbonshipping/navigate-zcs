# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import copy
import gzip
import logging
import os
import pickle
import timeit

logger = logging.getLogger(__name__)

_STRIPPED_NODE_DICTS = ('plots', 'reports')


class PlotData:
    """
    Container that captures all simulation state needed by plot functions.

    Stores references to manager data after simulation completes, enabling
    plot generation without re-running the simulation. Can be serialized
    to disk via pickle for later replotting.
    """

    def __init__(self):
        self._dateline = None
        self._timeline = None
        self.profile = None
        self.nodes = None
        self.general_nodes = None
        self._deck_directory = None
        self._plot_configs = []

    @classmethod
    def from_manager(cls, manager):
        """
        Create a PlotData instance from a completed SimulationManager.

        Parameters
        ----------
        manager : SimulationManager
            The manager after simulation has completed.

        Returns
        -------
        PlotData
            A new PlotData instance with references to manager state.
        """
        plot_data = cls()
        plot_data._dateline = manager._dateline
        plot_data._timeline = manager._timeline
        plot_data.profile = manager.profile
        plot_data.nodes = manager.nodes
        plot_data.general_nodes = manager.general_nodes
        plot_data._deck_directory = manager._parser._deck_directory
        plot_data._plot_configs = [
            {"name": name, "directory": node._directory, "selected_plots": set(node._selected_plots)}
            for name, node in manager.nodes.plots.items()
        ]
        return plot_data

    def __getstate__(self):
        """Strip node dicts not needed for plotting before pickling."""
        state = self.__dict__.copy()
        if state.get('nodes') is not None:
            nodes = copy.copy(state['nodes'])
            for attr in _STRIPPED_NODE_DICTS:
                setattr(nodes, attr, {})
            state['nodes'] = nodes
        return state

    def save(self, directory=None):
        """
        Serialize PlotData to a gzip-compressed pickle file.

        Parameters
        ----------
        directory : str, optional
            Directory to save to. Defaults to the deck directory.
        """
        if directory is None:
            directory = self._deck_directory

        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, 'plot_data.pkl')

        start = timeit.default_timer()
        with gzip.open(path, 'wb') as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        elapsed = timeit.default_timer() - start

        size_mb = os.path.getsize(path) / (1024 * 1024)
        logger.info(
            f"Exported plot data to '{path}' ({size_mb:.1f} MB, {elapsed:.1f}s)"
        )

    @classmethod
    def load(cls, path):
        """
        Load PlotData from a gzip-compressed pickle file.

        Parameters
        ----------
        path : str
            Path to the pickle file or to a directory containing plot_data.pkl.

        Returns
        -------
        PlotData
            The deserialized PlotData instance.
        """
        if os.path.isdir(path):
            path = os.path.join(path, 'plot_data.pkl')

        with gzip.open(path, 'rb') as f:
            plot_data = pickle.load(f)

        logger.info(f"Loaded plot data from '{path}'")
        return plot_data

    def get_dateline(self):
        return self._dateline

    def get_timeline(self):
        return self._timeline

    def get_deck_directory(self):
        return self._deck_directory

    def get_plot_configs(self):
        return self._plot_configs
