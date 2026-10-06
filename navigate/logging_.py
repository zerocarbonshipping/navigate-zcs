# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Run logging: the log file, the console preamble and the end-of-run summary."""

from __future__ import annotations

import logging
import os
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from tabulate import tabulate

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

_MAX_DIGEST_WARNINGS = 20

_COUNT_HANDLER: _CountingHandler | None = None
_DEDUP_FILTER: _DeduplicatingFilter | None = None
_LOG_FILE_NAME: str | None = None


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
    filename = Path(path).with_suffix(".log")
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
