# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import gzip
import logging
import os
import pickle
import timeit
from dataclasses import dataclass
from typing import TYPE_CHECKING

from navigate.exceptions import PlotDataError

if TYPE_CHECKING:
    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.core.profiles.manager_profile import ManagerProfile
    from navigate.util.types_ import DateArray, FloatArray

logger = logging.getLogger(__name__)

_STRIPPED_NODE_DICTS = ("plots", "reports")


@dataclass(eq=False, repr=False)
class PlotData:
    """Container that captures all simulation state needed by plot functions."""

    dateline: DateArray
    timeline: FloatArray
    profile: ManagerProfile
    nodes: Nodes
    general_nodes: GeneralNodes
    deck_directory: str
    plot_configs: list[dict]

    @classmethod
    def from_manager(cls, manager) -> PlotData:
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
        plot_configs = [
            {
                "name": name,
                "directory": node.directory,
                "selected_plots": set(node.selected_plots),
            }
            for name, node in manager.nodes.plots.items()
        ]
        return cls(
            dateline=manager.dateline,
            timeline=manager.timeline,
            profile=manager.profile,
            nodes=manager.nodes,
            general_nodes=manager.general_nodes,
            deck_directory=manager.parser.deck_directory,
            plot_configs=plot_configs,
        )

    def __getstate__(self) -> dict:
        """Strip node dicts not needed for plotting before pickling."""
        state = self.__dict__.copy()
        nodes = copy.copy(state["nodes"])
        for attr in _STRIPPED_NODE_DICTS:
            setattr(nodes, attr, {})
        state["nodes"] = nodes
        return state

    def save(self, directory: str | None = None) -> None:
        """
        Serialize PlotData to a gzip-compressed pickle file.

        Parameters
        ----------
        directory : str, optional
            Directory to save to. Defaults to the deck directory.
        """
        if directory is None:
            directory = self.deck_directory

        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "plot_data.pkl")

        start = timeit.default_timer()
        with gzip.open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        elapsed = timeit.default_timer() - start

        size_mb = os.path.getsize(path) / (1024 * 1024)
        logger.info(
            "Exported plot data to '%s' (%.1f MB, %.1fs)", path, size_mb, elapsed
        )

    @classmethod
    def load(cls, path: str) -> PlotData:
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

        Raises
        ------
        PlotDataError
            If the file is not a valid pickle, is unreadable by this
            Navigate version, or the unpickled object does not hold a
            PlotData instance.
        """
        if os.path.isdir(path):
            path = os.path.join(path, "plot_data.pkl")

        try:
            with gzip.open(path, "rb") as f:
                plot_data = pickle.load(f)
        except (
            pickle.UnpicklingError,
            EOFError,
            AttributeError,
            ImportError,
            IndexError,
            gzip.BadGzipFile,
            MemoryError,
            OverflowError,
            TypeError,
            ValueError,
        ) as err:
            raise PlotDataError(
                f"'{path}' cannot be read as the plot data of this Navigate "
                f"version: {err}"
            ) from err

        if not isinstance(plot_data, cls):
            raise PlotDataError(
                f"'{path}' holds a {type(plot_data).__name__}, not the plot data of "
                "a Navigate run."
            )

        logger.info("Loaded plot data from '%s'", path)
        return plot_data
