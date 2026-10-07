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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Navigate")
    parser.add_argument(
        "-p",
        "--profile",
        action="store_true",
        help="Profile the computational performance of the simulation. Note that this"
        " suppresses all output that is not directly related to the simulation.",
    )
    parser.add_argument(
        "-s",
        "--suppress-plots",
        action="store_true",
        help="Suppress the generation of plots at the end of the simulation. Note that"
        " Excel based output reports will still be generated.",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="INFO",
        choices=LOG_LEVELS,
        help="Set the level of how much output is generated for the .log file. DEBUG"
        " also prints the full traceback to the console if the run fails.",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        type=Path,
        metavar="DIR",
        default=os.environ.get(ASSUMPTIONS_ENV_VAR),
        help=f"Folder location for assumptions that may be imported. "
        f"Can also be set with the environment variable '{ASSUMPTIONS_ENV_VAR}'",
    )
    parser.add_argument(
        "--solver",
        choices=SOLVER_BACKENDS,
        help="Solver backend: 'auto' tries Gurobi then falls back to HiGHS, "
        "'gurobi' prefers Gurobi (falls back to HiGHS if unlicensed), "
        "'highs' skips Gurobi and uses HiGHS directly. Default: auto.",
    )
    parser.add_argument(
        "filename",
        type=Path,
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
        A usage error exits with 2 through parser.error instead.
    """
    parser = _build_parser()
    args = parser.parse_args()
    _validate_args(parser, args)

    try:
        with RunLog(args.filename, args.log_level) as run_log:
            try:
                return _dispatch(args, run_log)
            except _FATAL_ERRORS as exc:
                # recorded while the run log is open; the console report below
                # also covers an error that kept the log from opening
                logger.exception("Fatal error: %s", exc)
                raise
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except _FATAL_ERRORS as exc:
        _print_error(exc, debug=(args.log_level == "DEBUG"))
        return 1


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """
    Validate the CLI paths up front so bad input fails fast with a clear message.

    Exits via parser.error() (exit code 2) on the first problem found.

    Parameters
    ----------
    parser
        Parser used to report usage-style errors.
    args
        Parsed CLI arguments.
    """
    if args.data_dir is not None and not args.data_dir.is_dir():
        parser.error(
            f"assumptions data directory not found: '{args.data_dir}' "
            f"(set via -d/--data-dir or the {ASSUMPTIONS_ENV_VAR} environment variable)"
        )

    _validate_file(parser, args.filename)


def _validate_file(parser: argparse.ArgumentParser, path: Path) -> None:
    """
    Exit via parser.error() (code 2) unless `path` is an existing '.nav' deck file.

    Parameters
    ----------
    parser
        Parser used to report usage-style errors.
    path
        Path to validate.
    """
    if not path.exists():
        parser.error(f"deck file not found: '{path}'")

    if path.is_dir():
        parser.error(f"deck file is a directory, not a file: '{path}'")

    if path.suffix.lower() != ".nav" or not path.stem.strip("."):
        parser.error(f"deck file must have a '.nav' extension: '{path}'")


def _dispatch(args: argparse.Namespace, run_log: RunLog) -> int:
    print_preamble()
    run = functools.partial(
        run_deck, args.filename, data_dir=args.data_dir, solver=args.solver
    )

    if args.profile:
        # a profiled run ends its console output with the profile statistics, so
        # it prints no warning notice
        with cProfile.Profile() as profiler:
            run(plots=False)

        _report_profile(profiler, args.filename.resolve().parent)
        run_log.log_summary()
        return 0

    run(plots=not args.suppress_plots)

    run_log.log_summary()
    run_log.print_warning_notice()

    return 0


def _print_error(exc: Exception, debug: bool) -> None:
    """
    Print a fatal error to the console.

    The run log has recorded the full traceback, unless the error kept the log
    from opening; the console gets either a one-line message or, with -l DEBUG,
    the full traceback.

    Parameters
    ----------
    exc
        The error that terminated the run.
    debug
        Whether the full traceback should be printed to the console.
    """
    if debug:
        traceback.print_exc()
    else:
        print(f"Error: {exc}", file=sys.stderr)


def _report_profile(profiler: cProfile.Profile, deck_directory: Path) -> None:
    """
    Dump the profile statistics next to the deck and print the costliest calls.

    Parameters
    ----------
    profiler
        Profiler that has finished the run.
    deck_directory
        Folder the 'profile' statistics file is written to.
    """
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats(str(deck_directory / "profile"))
    stats.print_stats(100)
