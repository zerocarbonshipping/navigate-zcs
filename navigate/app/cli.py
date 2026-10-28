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
import re
import sys
import traceback
from pathlib import Path

from navigate.app.logs import LOG_LEVELS, RunLog, print_preamble
from navigate.driver import SOLVER_BACKENDS, run_deck
from navigate.exceptions import NavigateError

ASSUMPTIONS_ENV_VAR = "ASSUMPTIONS_DATA_DIR"

_DECK_SUFFIXES = (".nav", ".unc")

# a name --set gives a value, as a deck writes it between two '%'
_PARAM_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

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

    if path.suffix.lower() not in _DECK_SUFFIXES or not path.stem.strip("."):
        raise argparse.ArgumentTypeError(
            f"must have a '.nav' or '.unc' extension: '{path}'"
        )

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


def _param(value: str) -> tuple[str, str]:
    """Return the name and value of NAME=VALUE; raise ArgumentTypeError if malformed."""
    name, separator, text = value.partition("=")

    if not separator:
        raise argparse.ArgumentTypeError(f"must be NAME=VALUE: '{value}'")

    if not _PARAM_NAME.fullmatch(name):
        raise argparse.ArgumentTypeError(
            "NAME must be letters, digits and underscores, not starting with a "
            f"digit: '{name}'"
        )

    return name, text


def _run_name(value: str) -> str:
    """Return the run name; raise ArgumentTypeError unless it is a file name."""
    if not value or Path(value).name != value:
        raise argparse.ArgumentTypeError(f"must be a file name, not a path: '{value}'")

    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Navigate")
    parser.add_argument(
        "-p",
        "--profile",
        action="store_true",
        help="Profile the run, write the statistics to the file '<name>.prof' in "
        "the output folder and print the 100 functions with the highest cumulative "
        "time. A profiled run prints no warning count.",
    )
    parser.add_argument(
        "--set",
        type=_param,
        action="append",
        default=[],
        dest="params",
        metavar="NAME=VALUE",
        help="Replace each %%NAME%% in the deck and the files it reads with VALUE, "
        "as text, before they are read. Repeat for each name; a %%NAME%% left "
        "without a value outside a comment is an error. A run with --set writes "
        "its log into the 'logs' and its results file into the 'parquets' "
        "subfolder of the output folder, as one of many runs of its deck.",
    )
    parser.add_argument(
        "--name",
        type=_run_name,
        help="Name of the run, the stem of its log, results, profile and "
        "infeasible-LP files. Default: the deck's file name without extension.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        metavar="DIR",
        help="Folder the log, results, profile and infeasible-LP files are written to, "
        "created if missing. Default: the deck's folder.",
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
        help="Path to the .nav or .unc simulation deck to run.",
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
    parser = _build_parser()
    args = parser.parse_args()
    args.params = _params_by_name(parser, args.params)

    # the defaults derive from the deck: its file name and its folder; a run with
    # --set values is one of many of its deck, so its log and results file go
    # into subfolders of the output folder
    args.name = args.name or args.filename.stem
    args.output_dir = args.output_dir or args.filename.parent
    log_path = args.output_dir / ("logs" if args.params else "") / f"{args.name}.log"
    args.results = (
        args.output_dir / ("parquets" if args.params else "") / f"{args.name}.parquet"
    )

    try:
        with RunLog(log_path, args.log_level) as run_log:
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
        params=args.params,
        name=args.name,
        output_dir=args.output_dir,
    )

    # a profiled run ends its console output with the profile statistics, so it
    # prints no warning count
    if args.profile:
        with cProfile.Profile() as profiler:
            run()

        _report_profile(profiler, args.output_dir / f"{args.name}.prof")
        run_log.log_summary()
    else:
        run()

        run_log.log_summary()
        run_log.print_warning_notice()


def _params_by_name(
    parser: argparse.ArgumentParser, params: list[tuple[str, str]]
) -> dict[str, str]:
    """Return the --set values by name; exit through the parser on a name set twice."""
    by_name: dict[str, str] = {}

    for name, value in params:
        if name in by_name:
            parser.error(f"argument --set: '{name}' is set twice")

        by_name[name] = value

    return by_name


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
