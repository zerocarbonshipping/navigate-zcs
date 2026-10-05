# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import gzip
import logging
import os
import pickle
import timeit
import zlib
from dataclasses import dataclass, fields
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
            deck_directory=manager.deck_directory,
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
        path
            Path to the pickle file or to a directory containing plot_data.pkl.

        Returns
        -------
        PlotData
            The deserialized PlotData instance.

        Raises
        ------
        OSError
            The file cannot be opened or is not gzip-compressed.
        PlotDataError
            The gzip stream is corrupt, its content is not a pickle, it
            cannot be unpickled by this Navigate version, it does not hold
            a PlotData instance, or it holds a PlotData instance missing
            fields that this Navigate version expects.
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
            OverflowError,
            TypeError,
            ValueError,
            zlib.error,
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

        missing = [
            field.name for field in fields(cls) if field.name not in plot_data.__dict__
        ]
        if missing:
            raise PlotDataError(
                f"'{path}' was written by a Navigate version whose plot data "
                f"differs from this one: missing {', '.join(missing)}."
            )

        logger.info("Loaded plot data from '%s'", path)
        return plot_data
