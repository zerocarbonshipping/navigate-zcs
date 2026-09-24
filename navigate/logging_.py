# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Run logging: the log file, the console preamble and the end-of-run summary."""

from __future__ import annotations

import logging
import os
import time as time_module
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from math import floor, log10
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from tabulate import tabulate

from navigate.core.unit import YEAR_TO_DAYS
from navigate.util import TOLERANCE

if TYPE_CHECKING:
    from navigate.util import FloatArray

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
HLINE = "=" * 120

_MAX_DIGEST_WARNINGS = 20

_COUNT_HANDLER: _CountingHandler | None = None
_DEDUP_FILTER: _DeduplicatingFilter | None = None
_LOG_FILE_NAME: str | None = None
_WALL_START_TIME: float | None = None


class _DeduplicatingFilter(logging.Filter):
    """
    Suppress duplicate WARNING+ messages in the file log.

    The first occurrence passes through; subsequent identical messages
    are counted but not written. INFO and DEBUG always pass.
    """

    def __init__(self) -> None:
        super().__init__()
        self.seen: set[str] = set()  # messages already let through
        self.suppressed: int = 0  # duplicates dropped
        self.unique_warnings: list[str] = []  # messages kept for the digest

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.WARNING:
            return True
        key = record.getMessage()
        if key in self.seen:
            self.suppressed += 1
            return False
        self.seen.add(key)
        if len(self.unique_warnings) < _MAX_DIGEST_WARNINGS:
            self.unique_warnings.append(key)
        return True


class _CountingHandler(logging.Handler):
    """Tally the records emitted per log level, without writing them anywhere."""

    def __init__(self) -> None:
        super().__init__()
        self.counter: Counter[str] = Counter()  # records seen per level name

    def emit(self, record: logging.LogRecord) -> None:
        self.counter[record.levelname] += 1


def setup_logger(path: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Configure the root logger to write a log file next to the deck.

    Parameters
    ----------
    path
        Path to the simulation deck; the log file takes its stem.
    level
        Lowest level written to the log file.

    Returns
    -------
    logging.Logger
        The configured root logger.
    """
    # splitext finds no extension in a name whose stem is only dots, where
    # with_suffix replaces one: '..nav' logs to '..nav.log', not '..log'
    filename = os.path.splitext(path)[0] + ".log"
    file_handler = logging.FileHandler(filename, mode="w")

    global _LOG_FILE_NAME
    _LOG_FILE_NAME = os.path.basename(filename)

    global _COUNT_HANDLER, _DEDUP_FILTER
    _COUNT_HANDLER = _CountingHandler()
    _DEDUP_FILTER = _DeduplicatingFilter()

    # the file handler alone deduplicates, so the counts stay honest
    file_handler.addFilter(_DEDUP_FILTER)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[file_handler, _COUNT_HANDLER],
        force=True,
    )

    return logging.getLogger()


def print_preamble() -> None:
    """Print the banner and the package version to the console."""
    try:
        pkg_version = version("navigate-zcs")
    except PackageNotFoundError:
        pkg_version = "Debug"

    file = Path(__file__).parent / "preamble.txt"
    with open(file) as f:
        preamble = f.read()
    print(preamble.format(pkg_version))


def log_time_step_breaker(
    logger: logging.Logger, idx: int, date: np.datetime64, time: float
) -> None:
    """
    Log the banner separating one time-step from the next.

    Parameters
    ----------
    logger
        Logger to write to.
    idx
        Index of the time-step.
    date
        Date of the time-step.
    time
        Days since the start of the simulation.
    """
    elapsed_time = (
        time_module.perf_counter() - _WALL_START_TIME if _WALL_START_TIME else 0
    )

    msg = (
        f"Time-step: {idx}, current date: {date}. "
        f"{int(time)} days "
        f"({int(round(time / YEAR_TO_DAYS, 0))} years) "
        "since start of simulation. "
        f"Wall time since start: {elapsed_time:,.1f} s"
    )

    logger.info(_wrap_in_hlines(msg))


def log_extrapolate_bounds(
    logger: logging.Logger, node: object, x: FloatArray, a: float, b: float
) -> None:
    """
    Warn that a table look-up reached beyond the tabulated range.

    Parameters
    ----------
    logger
        Logger to write to.
    node
        Node owning the table, named in the message.
    x
        Look-up values, reported when there are few enough to read.
    a
        Lower limit of the tabulated range.
    b
        Upper limit of the tabulated range.
    """
    # node is typed as object because the table mixins calling this are not
    # Node subclasses statically; it is only formatted into the message
    info = f" Value was {x}." if x.size < 5 else ""

    logger.warning(
        "%s: Extrapolating beyond table limits (%s, %s).%s", node, a, b, info
    )


def log_start_of_simulation(logger: logging.Logger, date: np.datetime64) -> None:
    """
    Log the banner opening the simulation and start the wall clock.

    Parameters
    ----------
    logger
        Logger to write to.
    date
        Date the simulation starts from.
    """
    global _WALL_START_TIME
    _WALL_START_TIME = time_module.perf_counter()

    logger.info(_wrap_in_hlines(f"Time-step: 0, starting simulation at date: {date}"))


def log_model_post_process(logger: logging.Logger) -> None:
    """
    Log the banner opening the post-processing of the model.

    Parameters
    ----------
    logger
        Logger to write to.
    """
    logger.info(_wrap_in_hlines("Post-process model after end of simulation"))


def log_fair_share_convergence(
    logger: logging.Logger,
    statistics: dict[str, list[float]],
    iterations: int,
    converged: bool,
) -> None:
    """
    Log the outcome of the fair-share bunkering algorithm and its iterations.

    Parameters
    ----------
    logger
        Logger to write to.
    statistics
        Convergence metric per name, each holding one value per iteration.
    iterations
        Number of iterations run.
    converged
        Whether the algorithm reached its convergence criterion.
    """
    headers = ["Iter.", *statistics.keys()]
    cols = list(statistics.values())
    rows = [
        [i + 1] + [str(_round_for_display(cols[c][i])) for c in range(len(cols))]
        for i in range(iterations)
    ]

    table = tabulate(rows, headers=headers, tablefmt="github", stralign="right")

    if converged:
        logger.info("Fair-share bunkering convergence status: Successful.")
        logger.debug("Fair-share bunkering convergence statistics:\n\n%s", table)
    else:
        msg = "Fair-share bunkering convergence status: Failure.\n"
        msg += f"Fair-share bunkering convergence statistics:\n\n{table}"
        logger.info(msg)


def _wrap_in_hlines(msg: str) -> str:
    """
    Frame a message in horizontal lines.

    Parameters
    ----------
    msg
        Message to frame.

    Returns
    -------
    str
        Framed message.
    """
    return "\n" + HLINE + "\n" + msg + "\n" + HLINE + "\n"


def get_log_counts() -> dict[str, int]:
    """
    Count the records logged so far.

    Returns
    -------
    dict[str, int]
        Number of records per level name, empty when no run has been set up.
    """
    if not _COUNT_HANDLER:
        return {}

    return {
        lvl: _COUNT_HANDLER.counter.get(lvl, 0)
        for lvl in set(LOG_LEVELS) | set(_COUNT_HANDLER.counter)
    }


def log_summary() -> str:
    """
    Build the end-of-run summary: the record counts and the warning digest.

    Returns
    -------
    str
        Summary table, extended with the unique warnings when any were logged.
    """
    counts = get_log_counts()

    rows = [[lvl, counts.get(lvl, 0)] for lvl in LOG_LEVELS if lvl in counts] + [
        [lvl, counts[lvl]] for lvl in counts if lvl not in LOG_LEVELS
    ]
    table = tabulate(
        rows, headers=["Level", "Count"], tablefmt="github", stralign="right"
    )

    summary = f"\nLog summary:\n{table}"

    if _DEDUP_FILTER and _DEDUP_FILTER.unique_warnings:
        n_unique = len(_DEDUP_FILTER.seen)
        n_suppressed = _DEDUP_FILTER.suppressed

        summary += (
            f"\n\nUnique warnings ({n_unique} unique, {n_suppressed} duplicates "
            f"suppressed):"
        )

        for i, msg in enumerate(_DEDUP_FILTER.unique_warnings, 1):
            short = (msg[:120] + "...") if len(msg) > 120 else msg
            summary += f"\n  {i}. {short}"

        if n_unique > _MAX_DIGEST_WARNINGS:
            summary += f"\n  ... and {n_unique - _MAX_DIGEST_WARNINGS} more"

    return summary


def print_warning_summary() -> None:
    """
    Print the number of logged warnings to the console.

    Points at the log file that setup_logger opened.
    """
    warnings = get_log_counts().get("WARNING", 0)

    if warnings and _LOG_FILE_NAME:
        print(f"{warnings} warning(s) logged - see '{_LOG_FILE_NAME}'.")


def _round_for_display(x: float) -> float:
    """
    Round off a value to the appropriate decimals for visual display.

    Parameters
    ----------
    x
        Value to be rounded for display.

    Returns
    -------
    float
        Rounded value.
    """
    abs_x = abs(x)

    if abs_x <= TOLERANCE:
        return 0

    significant = -floor(log10(abs_x))

    if significant <= 0:
        return int(np.round(x, 0))

    return float(np.round(x, significant))
