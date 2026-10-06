# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Render the registered plots of a run into PNG files."""

from __future__ import annotations

import logging
import os
import timeit
from math import floor
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

from navigate.output.plots._registry import PLOT_LABELS, PLOTS, plot_label
from navigate.output.plots._style import initialize_matplotlib

if TYPE_CHECKING:
    from navigate.core.nodes.plot import Plot
    from navigate.core.simulation_results import SimulationResults

logger = logging.getLogger(__name__)


def generate_plots(plot: Plot, results: SimulationResults, deck_directory: str) -> None:
    """
    Render the plots requested by one Plot node from the results of a run.

    Parameters
    ----------
    plot
        Plot node holding the output directory and selected plot labels.
    results
        Results of the finished run.
    deck_directory
        Directory of the simulation deck, base for the plot directory.
    """
    directory = os.path.join(deck_directory, plot.directory or "plots")
    selected_plots = plot.selected_plots or None  # an empty set selects all plots
    render_plots(results, directory=directory, selected_plots=selected_plots)


def render_plots(
    results: SimulationResults, directory: str, selected_plots: set[str] | None
) -> None:
    """
    Render the selected plots into a directory, logging each plot that fails.

    Parameters
    ----------
    results
        Results of the finished run.
    directory
        Directory to save the figures in.
    selected_plots
        Labels of the plots to render; None renders every plot.
    """
    initialize_matplotlib()
    start = timeit.default_timer()

    os.makedirs(directory, exist_ok=True)

    if results.dateline.size < 2:
        return

    if selected_plots is not None:
        for label in selected_plots - PLOT_LABELS:
            logger.warning("Plot label '%s' was requested but does not exist.", label)

    plot_errors = 0

    for plot_function in PLOTS:
        label = plot_label(plot_function)
        if selected_plots is not None and label not in selected_plots:
            continue

        try:
            plot_function(results, directory)
        except Exception as error:
            plot_errors += 1
            logger.error("Plot '%s' failed: %s", label, error)
            plt.close("all")

    if plot_errors > 0:
        logger.warning("Plot generation completed with %d error(s).", plot_errors)

    _print_elapsed_time(timeit.default_timer() - start, "plots")
    logger.info("Plots generated successfully.")


def _print_elapsed_time(elapsed: float, section: str) -> None:
    minutes = floor(elapsed / 60.0)
    seconds = int(elapsed - minutes * 60.0)

    print(f"Finished {section}, elapsed time: {minutes}m and {seconds}s.")
