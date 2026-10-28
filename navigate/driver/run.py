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
from navigate.output import SimulationResults, write_results
from navigate.parser import Parser
from navigate.simulation.time_stepping import Simulation
from navigate.util import YEAR, timedelta_to_days

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import numpy as np

# the solver names run_deck takes, each with the backend it selects
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
    results_file: Path | None = None,
    params: Mapping[str, str] | None = None,
    name: str | None = None,
    output_dir: Path | None = None,
) -> SimulationResults:
    """
    Run a deck and write its results file.

    Parameters
    ----------
    deck
        Path to the simulation deck.
    data_dir
        Assumptions data folder.
    solver
        Name of the solver backend, a key of SOLVER_BACKENDS, that overrides the
        deck's BunkerOptions setting, or None to keep the deck's setting.
    results_file
        Parquet file the full results are written to; '<name>.parquet' in the
        output folder by default.
    params
        Value of each %NAME% placeholder of the deck's files, as text.
    name
        Name of the run, the stem of its output files; the deck's stem by default.
    output_dir
        Folder the output is written to, created when missing; the deck's folder
        by default.

    Returns
    -------
    SimulationResults
        The results of the completed run.
    """
    # resolved as the parser resolves it, so the deck location matches the deck read
    deck_path = deck.resolve()
    run_name = name or deck_path.stem
    output_directory = output_dir or deck_path.parent

    output_directory.mkdir(parents=True, exist_ok=True)

    parser = Parser()
    parser.read_deck(deck_path, data_dir=data_dir, params=params)
    dates = parser.dates

    if solver is not None:
        parser.general_nodes.bunker_options.solver = SOLVER_BACKENDS[solver]

    start_time = timeit.default_timer()
    simulation = Simulation(
        parser.nodes,
        parser.general_nodes,
        dates,
        output_directory / f"{run_name}_bunkering_infeasible.lp",
    )
    simulation.initialize()

    for idx, date in enumerate(dates):
        _log_time_step(idx, date, dates[0], start_time)
        print(f"Date: {date}")

        inputs_changed = parser.read_events(date)
        simulation.step(inputs_changed)

    # the simulation ran the parser's nodes, which now hold their own results
    results = SimulationResults(
        dateline=dates,
        global_results=simulation.finish(),
        nodes=parser.nodes,
        general_nodes=parser.general_nodes,
    )

    results_path = results_file or output_directory / f"{run_name}.parquet"
    write_results(results, results_path, run_name, params or {})

    elapsed = _format_duration(timeit.default_timer() - start_time)

    print(f"Finished simulation, elapsed time: {elapsed}.")
    logger.info("Simulation completed successfully, elapsed time: %s.", elapsed)

    return results


def _log_time_step(
    idx: int, date: np.datetime64, start_date: np.datetime64, start_time: float
) -> None:
    days_elapsed = timedelta_to_days(date - start_date)
    years_elapsed = round(days_elapsed / YEAR)
    wall_time = timeit.default_timer() - start_time

    logger.info(
        "Time-step: %d, current date: %s. %d days (%d years) since start "
        "of simulation. Wall time since start: %.1f s",
        idx,
        date,
        days_elapsed,
        years_elapsed,
        wall_time,
        extra={"heading": True},
    )


def _format_duration(seconds: float) -> str:
    whole_minutes = math.floor(seconds / 60.0)
    whole_seconds = int(seconds - whole_minutes * 60.0)

    return f"{whole_minutes}m and {whole_seconds}s"
