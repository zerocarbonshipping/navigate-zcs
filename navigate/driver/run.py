# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Run a simulation deck: read it, step the model through its dates, write the output.

The CLI and the test suites that run decks in-process call run_deck.
"""

from __future__ import annotations

import logging
import math
import timeit
from typing import TYPE_CHECKING

from navigate.core.enum_ import SolverBackendID
from navigate.output import write_report
from navigate.parser import Parser
from navigate.simulation import Simulation
from navigate.util import YEAR, timedelta_to_days

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np

    from navigate.core import SimulationResults

# the names the solver choice goes by, for the CLI's '--solver' and run_deck's 'solver'
SOLVER_BACKENDS: dict[str, SolverBackendID] = {
    "auto": SolverBackendID.AUTOMATIC,
    "gurobi": SolverBackendID.GUROBI,
    "highs": SolverBackendID.HIGHS,
}

logger = logging.getLogger(__name__)


def run_deck(
    deck: Path,
    *,
    data_dir: Path | None = None,
    solver: str | None = None,
    plots: bool,
) -> SimulationResults:
    """
    Run a simulation deck and write the reports and, on request, the plots it defines.

    Parameters
    ----------
    deck
        Path to the simulation deck; the output is written next to it.
    data_dir
        Assumptions data folder.
    solver
        Name of the solver backend, a key of SOLVER_BACKENDS, that overrides the
        deck's BunkerOptions setting, or None to keep the deck's setting.
    plots
        Whether to render the plots the deck's Plot nodes request.

    Returns
    -------
    SimulationResults
        The results of the completed run.
    """
    # resolved as the parser resolves it, so the deck location matches the deck read
    deck_path = deck.resolve()
    deck_directory = str(deck_path.parent)

    parser = Parser()
    parser.read_deck(deck_path, data_dir=data_dir)
    parser.includes_necessary_information()

    if solver is not None:
        parser.general_nodes.bunker_options.solver = SOLVER_BACKENDS[solver]

    start_time = timeit.default_timer()
    simulation = Simulation(
        parser.nodes, parser.general_nodes, parser.dates, deck_directory
    )
    simulation.initialize()

    for idx, date in enumerate(parser.dates):
        _log_time_step(idx, date, parser.dates[0], start_time)
        parser.read_events(date)
        print(f"Date: {date}")
        simulation.step(date)

    results = simulation.finish()

    for report in results.nodes.reports.values():
        write_report(report, results, deck_directory, deck_path.stem)

    elapsed = _format_duration(timeit.default_timer() - start_time)

    print(f"Finished simulation, elapsed time: {elapsed}.")
    logger.info("Simulation completed successfully, elapsed time: %s.", elapsed)

    if plots:
        _render_plots(results, deck_directory)

    return results


def _log_time_step(
    idx: int, date: np.datetime64, start_date: np.datetime64, start_time: float
) -> None:
    days_elapsed = timedelta_to_days(date - start_date)

    logger.info(
        "Time-step: %d, current date: %s. %d days (%d years) since start "
        "of simulation. Wall time since start: %.1f s",
        idx,
        date,
        days_elapsed,
        round(days_elapsed / YEAR),
        timeit.default_timer() - start_time,
        extra={"heading": True},
    )


def _format_duration(seconds: float) -> str:
    whole_minutes = math.floor(seconds / 60.0)
    whole_seconds = int(seconds - whole_minutes * 60.0)

    return f"{whole_minutes}m and {whole_seconds}s"


def _render_plots(results: SimulationResults, deck_directory: str) -> None:
    # deferred so matplotlib only loads when plots are actually rendered
    from navigate.output.plots.render import generate_plots

    for plot_node in results.nodes.plots.values():
        generate_plots(plot_node, results, deck_directory)
