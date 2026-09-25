# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Run logging: the log file, the console preamble and the end-of-run summary."""

from __future__ import annotations

import logging
import os
import time
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
        self.seen: set[str] = set()
        self.suppressed: int = 0
        self.unique_warnings: list[str] = []

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
        self.counter: Counter[str] = Counter()

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
    # splitext treats a name whose stem is only dots as carrying no extension,
    # so '..nav' logs to '..nav.log'
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
        package_version = version("navigate-zcs")
    except PackageNotFoundError:
        package_version = "Debug"

    file = Path(__file__).parent / "preamble.txt"
    with open(file) as handle:
        preamble = handle.read()

    print(preamble.format(package_version))


def log_time_step_breaker(
    logger: logging.Logger, idx: int, date: np.datetime64, days_elapsed: float
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
    days_elapsed
        Days since the start of the simulation.
    """
    elapsed_time = time.perf_counter() - _WALL_START_TIME if _WALL_START_TIME else 0

    message = (
        f"Time-step: {idx}, current date: {date}. "
        f"{int(days_elapsed)} days "
        f"({int(round(days_elapsed / YEAR_TO_DAYS, 0))} years) "
        "since start of simulation. "
        f"Wall time since start: {elapsed_time:,.1f} s"
    )

    logger.info(_wrap_in_hlines(message))


def log_extrapolate_bounds(
    logger: logging.Logger,
    node: object,
    lookup_values: FloatArray,
    lower: float,
    upper: float,
) -> None:
    """
    Warn that a table look-up reached beyond the tabulated range.

    Parameters
    ----------
    logger
        Logger to write to.
    node
        Node owning the table, named in the message.
    lookup_values
        Look-up values, reported when there are few enough to read.
    lower
        Lower limit of the tabulated range.
    upper
        Upper limit of the tabulated range.
    """
    # node is typed as object because the table mixins calling this are not
    # Node subclasses statically; it is only formatted into the message
    info = f" Value was {lookup_values}." if lookup_values.size < 5 else ""

    logger.warning(
        "%s: Extrapolating beyond table limits (%s, %s).%s", node, lower, upper, info
    )


def log_start_of_simulation(logger: logging.Logger, date: np.datetime64) -> None:
    """
    Open the simulation section of the log, timing the run from here.

    Parameters
    ----------
    logger
        Logger to write to.
    date
        Date the simulation starts from.
    """
    global _WALL_START_TIME
    _WALL_START_TIME = time.perf_counter()

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
    columns = list(statistics.values())
    rows = [
        [i + 1] + [str(_round_for_display(column[i])) for column in columns]
        for i in range(iterations)
    ]

    table = tabulate(rows, headers=headers, tablefmt="github", stralign="right")

    if converged:
        logger.info("Fair-share bunkering convergence status: Successful.")
        logger.debug("Fair-share bunkering convergence statistics:\n\n%s", table)
    else:
        message = "Fair-share bunkering convergence status: Failure.\n"
        message += f"Fair-share bunkering convergence statistics:\n\n{table}"

        logger.info(message)


def _wrap_in_hlines(message: str) -> str:
    """
    Frame a message in horizontal lines.

    Parameters
    ----------
    message
        Message to frame.

    Returns
    -------
    str
        Framed message.
    """
    return "\n" + HLINE + "\n" + message + "\n" + HLINE + "\n"


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
        level: _COUNT_HANDLER.counter.get(level, 0)
        for level in set(LOG_LEVELS) | set(_COUNT_HANDLER.counter)
    }


def build_log_summary() -> str:
    """
    Build the end-of-run summary: the record counts and the warning digest.

    Returns
    -------
    str
        Summary table, extended with the unique warnings when any were logged.
    """
    counts = get_log_counts()

    rows = [
        [level, counts.get(level, 0)] for level in LOG_LEVELS if level in counts
    ] + [[level, counts[level]] for level in counts if level not in LOG_LEVELS]
    table = tabulate(
        rows, headers=["Level", "Count"], tablefmt="github", stralign="right"
    )

    summary = f"\nLog summary:\n{table}"

    if _DEDUP_FILTER and _DEDUP_FILTER.unique_warnings:
        unique_count = len(_DEDUP_FILTER.seen)
        suppressed_count = _DEDUP_FILTER.suppressed

        summary += (
            f"\n\nUnique warnings ({unique_count} unique, "
            f"{suppressed_count} duplicates suppressed):"
        )

        for i, message in enumerate(_DEDUP_FILTER.unique_warnings, 1):
            short = (message[:120] + "...") if len(message) > 120 else message
            summary += f"\n  {i}. {short}"

        if unique_count > _MAX_DIGEST_WARNINGS:
            summary += f"\n  ... and {unique_count - _MAX_DIGEST_WARNINGS} more"

    return summary


def print_warning_summary() -> None:
    """
    Print the number of logged warnings to the console.

    Points at the log file that setup_logger opened.
    """
    warnings = get_log_counts().get("WARNING", 0)

    if warnings and _LOG_FILE_NAME:
        print(f"{warnings} warning(s) logged - see '{_LOG_FILE_NAME}'.")


def _round_for_display(value: float) -> float:
    """
    Round off a value to the appropriate decimals for visual display.

    Parameters
    ----------
    value
        Value to be rounded for display.

    Returns
    -------
    float
        Rounded value.
    """
    magnitude = abs(value)

    if magnitude <= TOLERANCE:
        return 0

    significant = -floor(log10(magnitude))

    if significant <= 0:
        return int(np.round(value, 0))

    return float(np.round(value, significant))
