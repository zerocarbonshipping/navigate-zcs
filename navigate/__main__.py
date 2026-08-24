# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import argparse
import cProfile
import logging
import os
import pstats
import sys
import traceback
from pathlib import Path

from navigate.exceptions import NavigateError
from navigate.logging_ import LOG_LEVELS, log_summary, setup_logger
from navigate.manager import SimulationManager
from navigate.output.replot import replot

ASSUMPTIONS_ENV_VAR = "ASSUMPTIONS_DATA_DIR"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="Navigate")
    parser.add_argument("-p", "--profile", action="store_true",
                        help="Profile the computational performance of the simulation. Note that this suppresses"
                             " all output that is not directly related to the simulation.")
    parser.add_argument("-e", "--export-assumptions", action="store_true",
                        help="Export Assumptions in an Excel format.")
    parser.add_argument("-s", "--suppress-plots", action="store_true",
                        help="Suppress the generation of plots at the end of the simulation. Note that Excel based"
                             " output reports will still be generated.")
    parser.add_argument("-l", "--log-level", default="INFO", choices=LOG_LEVELS,
                        help="Set the level of how much output is generated for the .log file. DEBUG also"
                             " prints the full traceback to the console if the run fails.")
    parser.add_argument("-d", "--data-dir", type=Path, metavar="DIR",
                        default=os.environ.get(ASSUMPTIONS_ENV_VAR),
                        help=f"Folder location for assumptions that may be imported. "
                             f"Can also be set with the environment variable '{ASSUMPTIONS_ENV_VAR}'")
    parser.add_argument("--solver", default=None, choices=["auto", "gurobi", "highs"],
                        help="Solver backend: 'auto' tries Gurobi then falls back to HiGHS, "
                             "'gurobi' prefers Gurobi (falls back to HiGHS if unlicensed), "
                             "'highs' skips Gurobi and uses HiGHS directly. Default: auto.")
    parser.add_argument("-r", "--replot", type=Path, metavar="PATH",
                        help="Regenerate plots from previously exported plot data. "
                             "Provide path to directory containing plot_data.pkl "
                             "or to the file directly. Skips simulation. Optionally pass a "
                             ".inc file with Plot node(s) as the trailing argument to use "
                             "those instead of the plot nodes stored in the plot data.")
    parser.add_argument("filename", type=Path, metavar="PATH", nargs="?", default=None,
                        help="Path to the .nav simulation deck to run. When combined with "
                             "--replot, an optional .inc file with Plot node(s) to use instead "
                             "of the plot nodes stored in the plot data.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    _validate_args(parser, args)

    try:
        return _dispatch(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except (NavigateError, OSError) as exc:
        _handle_error(exc, debug=(args.log_level == "DEBUG"), log_to_file=not args.replot)
        return 1


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """
    Validate the CLI paths up front so bad input fails fast with a clear message.

    Exits via parser.error() (exit code 2) on the first problem found.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser used to report usage-style errors.
    args : argparse.Namespace
        Parsed CLI arguments.
    """

    if args.data_dir is not None and not args.data_dir.is_dir():
        parser.error(f"assumptions data directory not found: '{args.data_dir}' "
                     f"(set via -d/--data-dir or the {ASSUMPTIONS_ENV_VAR} environment variable)")

    if args.replot:
        if not args.replot.exists():
            parser.error(f"--replot path not found: '{args.replot}'")

        if args.filename is not None:
            _validate_file(parser, args.filename, kind="plot include file", suffix=".inc")

        return

    if not args.filename:
        parser.error("filename is required unless --replot is used")

    _validate_file(parser, args.filename, kind="deck file", suffix=".nav")


def _validate_file(parser: argparse.ArgumentParser, path: Path, *, kind: str, suffix: str) -> None:
    """
    Exit via parser.error() (exit code 2) unless `path` is an existing file with the given suffix.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser used to report usage-style errors.
    path : Path
        Path to validate.
    kind : str
        Human-readable description of the file used in error messages.
    suffix : str
        Required file extension, including the leading dot.
    """

    if not path.exists():
        parser.error(f"{kind} not found: '{path}'")

    if path.is_dir():
        parser.error(f"{kind} is a directory, not a file: '{path}'")

    if path.suffix.lower() != suffix:
        parser.error(f"{kind} must have a '{suffix}' extension: '{path}'")


def _dispatch(args: argparse.Namespace) -> int:
    if args.replot:
        replot(args.replot, plot_inc=args.filename, data_dir=args.data_dir)
        return 0

    setup_logger(args.filename, level=logging.getLevelName(args.log_level))
    deck = args.filename.resolve()

    if args.profile:
        _run_with_profile(deck, args)
        return 0

    manager = _run(deck, args)

    if args.export_assumptions:
        manager.export_assumptions()

    if not args.suppress_plots:
        manager.export_graphs()

    return 0


def _handle_error(exc: Exception, debug: bool, log_to_file: bool) -> None:
    """
    Report a fatal error at the CLI boundary.

    The full traceback is recorded in the run's .log file (ERROR passes every
    -l level); the console gets either a one-line message or, with -l DEBUG,
    the full traceback.

    Parameters
    ----------
    exc : Exception
        The error that terminated the run.
    debug : bool
        Whether the full traceback should be printed to the console.
    log_to_file : bool
        Whether this invocation set up the file logger (--replot never does).
        Guarded further by hasHandlers() in case setup_logger itself failed
        before installing handlers.
    """

    if log_to_file and logging.getLogger().hasHandlers():
        logging.getLogger(__name__).error("Fatal error: %s", exc, exc_info=True)

    if debug:
        traceback.print_exc()
    else:
        print(f"Error: {exc}", file=sys.stderr)


def _run(path: Path, args: argparse.Namespace) -> SimulationManager:
    manager = SimulationManager()
    manager.read_deck(path, args)
    manager.run()
    logger = logging.getLogger(__name__)
    logger.info(f"Simulation completed successfully in {manager.get_elapsed_time()} seconds.")
    logger.info(log_summary())
    return manager


def _run_with_profile(path: Path, args: argparse.Namespace) -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    _run(path, args)
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats(str(path.parent / "profile"))
    stats.print_stats(100)


if __name__ == "__main__":
    sys.exit(main())
