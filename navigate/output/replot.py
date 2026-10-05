# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Render the plots of a finished run again from its saved plot data (--replot)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from navigate.exceptions import PlotDataError
from navigate.output.plot_data import PlotData

if TYPE_CHECKING:
    from pathlib import Path

    from navigate.output.plot_data import PlotConfig


def replot(
    path: Path, plot_inc: Path | None = None, data_dir: Path | None = None
) -> None:
    """
    Render the plots stored in, or included alongside, saved plot data.

    Parameters
    ----------
    path
        Path to the plot data file or to a directory containing plot_data.pkl.
    plot_inc
        Include file whose Plot nodes replace the plot configurations stored in
        the plot data, or None to render the stored ones.
    data_dir
        Assumptions data folder the include file may import from.

    Raises
    ------
    OSError
        If the file at path cannot be opened or is not gzip-compressed.
    PlotDataError
        If the file at path cannot be read as the plot data of this Navigate
        version, or there is no plot configuration to render.
    """
    # deferred so the CLI loads matplotlib only when it renders plots (see also
    # simulation.py)
    from navigate.output.plots.render import render_plots

    plot_data = PlotData.load(str(path))

    if plot_inc is not None:
        configs = _plot_configs_from_include(plot_inc, data_dir)
    else:
        configs = plot_data.plot_configs

    if not configs:
        if plot_inc is not None:
            raise PlotDataError(
                f"No Plot nodes were found in the include file '{plot_inc}'."
            )
        raise PlotDataError(
            "The plot data contains no plot configurations (the .nav deck that "
            "produced it defined no Plot nodes). Provide a .inc file with one or more "
            "Plot nodes as an additional argument to replot."
        )

    deck_directory = plot_data.deck_directory
    for config in configs:
        directory = (
            os.path.join(deck_directory, config["directory"])
            if config["directory"]
            else None
        )
        render_plots(
            plot_data,
            directory=directory,
            selected_plots=config["selected_plots"] or None,
        )


def _plot_configs_from_include(
    plot_inc: Path, data_dir: Path | None
) -> list[PlotConfig]:
    from navigate.parser.parser import Parser

    plot_nodes = Parser.parse_plot_nodes(plot_inc, data_dir=data_dir)
    return [
        {
            "name": name,
            "directory": node.directory,
            "selected_plots": set(node.selected_plots),
        }
        for name, node in plot_nodes.items()
    ]
