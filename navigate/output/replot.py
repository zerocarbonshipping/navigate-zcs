# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from navigate.exceptions import PlotDataError


def replot(path: Path, plot_inc: Path | str | None = None, data_dir: Path | str | None = None) -> None:
    from navigate.output.plot_data import PlotData
    from navigate.output.plots.render import render_plots

    plot_data = PlotData.load(str(path))

    if plot_inc is not None:
        configs = _plot_configs_from_include(plot_inc, data_dir)
    else:
        configs = plot_data.get_plot_configs()

    if not configs:
        if plot_inc is not None:
            raise PlotDataError(f"No Plot nodes were found in the include file '{plot_inc}'.")
        raise PlotDataError(
            "The plot data contains no plot configurations (the .nav deck that produced it "
            "defined no Plot nodes). Provide a .inc file with one or more Plot nodes as an "
            "additional argument to replot."
        )

    deck_directory = plot_data.get_deck_directory()
    for config in configs:
        directory = os.path.join(deck_directory, config["directory"]) if config["directory"] else None
        render_plots(plot_data, directory=directory, selected_plots=config["selected_plots"] or None)


def _plot_configs_from_include(plot_inc: Path | str, data_dir: Path | str | None) -> list[dict]:
    from navigate.parser.parser import Parser

    plot_nodes = Parser.parse_plot_nodes(plot_inc, data_dir=data_dir)
    return [
        {"name": name, "directory": node._directory, "selected_plots": set(node._selected_plots)}
        for name, node in plot_nodes.items()
    ]
