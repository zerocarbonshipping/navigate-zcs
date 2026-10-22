# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The navigate command line: run a simulation deck."""

from __future__ import annotations

import argparse
import cProfile
import functools
import logging
import os
import pstats
import sys
import traceback
from pathlib import Path

from navigate.app.logs import LOG_LEVELS, RunLog, print_preamble
from navigate.driver import SOLVER_BACKENDS, run_deck
from navigate.exceptions import NavigateError

ASSUMPTIONS_ENV_VAR = "ASSUMPTIONS_DATA_DIR"

# the errors a run reports: logged with their traceback, printed to the console
_FATAL_ERRORS = (NavigateError, OSError)

logger = logging.getLogger(__name__)


def _deck_file(value: str) -> Path:
    """Return the deck path; raise ArgumentTypeError unless it is an existing deck."""
    path = Path(value)

    if not path.exists():
        raise argparse.ArgumentTypeError(f"file not found: '{path}'")

    if path.is_dir():
        raise argparse.ArgumentTypeError(f"a directory, not a file: '{path}'")

    if path.suffix.lower() != ".nav" or not path.stem.strip("."):
        raise argparse.ArgumentTypeError(f"must have a '.nav' extension: '{path}'")

    return path


def _data_dir(value: str) -> Path:
    """Return the folder path; raise ArgumentTypeError unless it is a directory."""
    path = Path(value)

    if not path.is_dir():
        raise argparse.ArgumentTypeError(
            f"folder not found: '{path}' (given with -d/--data-dir "
            f"or the {ASSUMPTIONS_ENV_VAR} environment variable)"
        )

    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Navigate")
    parser.add_argument(
        "-p",
        "--profile",
        action="store_true",
        help="Profile the run, write the statistics to the file 'profile' next to "
        "the deck and print the 100 functions with the highest cumulative time. A "
        "profiled run renders no plots and prints no warning count.",
    )
    parser.add_argument(
        "-s",
        "--suppress-plots",
        action="store_true",
        help="Skip the plots at the end of the run. The reports are still written, "
        "in each Report's file format.",
    )
    parser.add_argument(
        "-o",
        "--results",
        type=Path,
        metavar="FILE",
        help="Parquet file the full results of the run are written to, to be opened "
        "with Lantern. Default: '<deck>.parquet' next to the deck.",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="INFO",
        choices=LOG_LEVELS,
        help="Set the level of how much output is generated for the .log file. DEBUG "
        "also prints the full traceback to the console if the run fails.",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        type=_data_dir,
        metavar="DIR",
        default=os.environ.get(ASSUMPTIONS_ENV_VAR),
        help="Folder location for assumptions that may be imported. "
        f"Can also be set with the environment variable '{ASSUMPTIONS_ENV_VAR}'.",
    )
    parser.add_argument(
        "--solver",
        choices=SOLVER_BACKENDS,
        help="Solver backend: 'auto' tries Gurobi then falls back to HiGHS, "
        "'gurobi' prefers Gurobi (falls back to HiGHS if unlicensed), "
        "'highs' skips Gurobi and uses HiGHS directly. Without the flag, the "
        "deck's BunkerOptions Solver applies.",
    )
    parser.add_argument(
        "filename",
        type=_deck_file,
        metavar="PATH",
        help="Path to the .nav simulation deck to run.",
    )
    return parser


def main() -> int:
    """
    Run the command line on the arguments the process was started with.

    Returns
    -------
    int
        The exit code: 0 on success, 1 on a reported error, 130 on interrupt.
        A usage error exits with 2 through argparse instead.
    """
    args = _build_parser().parse_args()

    try:
        with RunLog(args.filename, args.log_level) as run_log:
            try:
                _run(args, run_log)
            except _FATAL_ERRORS as exc:
                # recorded while the run log is open; the console report below
                # also covers an error that kept the log from opening
                logger.exception("Fatal error: %s", exc)
                raise
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except _FATAL_ERRORS as exc:
        if args.log_level == "DEBUG":
            traceback.print_exc()
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


def _run(args: argparse.Namespace, run_log: RunLog) -> None:
    print_preamble()
    run = functools.partial(
        run_deck,
        args.filename,
        data_dir=args.data_dir,
        solver=args.solver,
        results_file=args.results,
    )

    # a profiled run ends its console output with the profile statistics, so it
    # prints no warning count
    if args.profile:
        with cProfile.Profile() as profiler:
            run(plots=False)

        _report_profile(profiler, args.filename.with_name("profile"))
        run_log.log_summary()
    else:
        run(plots=not args.suppress_plots)

        run_log.log_summary()
        run_log.print_warning_notice()


def _report_profile(profiler: cProfile.Profile, path: Path) -> None:
    """
    Dump the profile statistics to `path` and print the costliest functions.

    Parameters
    ----------
    profiler
        Profiler that has finished the run.
    path
        File the profile statistics are written to.
    """
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats(path)
    stats.print_stats(100)
