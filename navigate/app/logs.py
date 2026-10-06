# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The run log of a CLI run: its file, warning ledger and summary, and the preamble.

The CLI in ``navigate.__main__`` holds a ``RunLog`` open for the whole run; the
modules it runs log through their own module loggers and never import this one.
"""

from __future__ import annotations

import logging
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from math import floor, log10
from pathlib import Path
from typing import TYPE_CHECKING, Self, override

import numpy as np
from tabulate import tabulate

from navigate.util import TOLERANCE

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from types import TracebackType

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

_LINE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_TIME_FORMAT = "%H:%M:%S"
_HLINE = "=" * 120

_MAX_DIGEST_WARNINGS = 20
_MAX_DIGEST_LENGTH = 120


class RunLog:
    """
    Write the log file of a run from every record the root logger handles while open.

    Parameters
    ----------
    path
        Path to the simulation deck; the log file takes it with a '.log' suffix.
    level
        Name of the lowest level logged, one of LOG_LEVELS.
    """

    def __init__(self, path: Path, level: str) -> None:
        self._filename: Path = path.with_suffix(".log")
        self._level: str = level
        self._ledger: _WarningLedger = _WarningLedger()

        # set on entering
        self._handler: logging.FileHandler
        self._previous_level: int

    def __enter__(self) -> Self:
        # the file opens before the root logger changes, so a file that cannot be
        # opened leaves the logging configuration as it was
        handler = logging.FileHandler(self._filename, mode="w")
        handler.setFormatter(_RunLogFormatter())
        # a filter on the handler, unlike one on a logger, sees the records that
        # propagate from every module logger
        handler.addFilter(self._ledger)

        # a record below the root's level is never created, so the level is set
        # on the root rather than on the handler
        root = logging.getLogger()
        self._previous_level = root.level
        root.addHandler(handler)
        root.setLevel(self._level)
        self._handler = handler

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        root = logging.getLogger()
        root.removeHandler(self._handler)
        root.setLevel(self._previous_level)
        self._handler.close()

    def build_summary(self) -> str:
        """
        Build the end-of-run summary: the record counts and the warning digest.

        Returns
        -------
        str
            Count of the records logged so far per level, extended with the unique
            warnings when any were logged.
        """
        ledger = self._ledger
        counts = ledger.counts
        levels = LOG_LEVELS + [level for level in counts if level not in LOG_LEVELS]
        rows = [[level, counts[level]] for level in levels]
        table = tabulate(
            rows, headers=["Level", "Count"], tablefmt="github", stralign="right"
        )

        summary = f"\nLog summary:\n{table}"

        if not ledger.seen:
            return summary

        unique_count = len(ledger.seen)
        summary += (
            f"\n\nUnique warnings ({unique_count} unique, "
            f"{ledger.suppressed} duplicates suppressed):"
        )

        for i, message in enumerate(ledger.digest, 1):
            short = (
                message[:_MAX_DIGEST_LENGTH] + "..."
                if len(message) > _MAX_DIGEST_LENGTH
                else message
            )
            summary += f"\n  {i}. {short}"

        if unique_count > _MAX_DIGEST_WARNINGS:
            summary += f"\n  ... and {unique_count - _MAX_DIGEST_WARNINGS} more"

        return summary

    def print_warning_notice(self) -> None:
        """Print the number of warnings logged so far to the console, if any were."""
        warnings = self._ledger.counts["WARNING"]

        if warnings:
            print(f"{warnings} warning(s) logged - see '{self._filename.name}'.")


class _WarningLedger(logging.Filter):
    """Count the records of a run per level, and drop the repeats of a warning."""

    def __init__(self) -> None:
        super().__init__()
        self.counts: Counter[str] = Counter()
        self.seen: set[str] = set()
        self.digest: list[str] = []
        self.suppressed: int = 0

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Count a record, and drop it where it repeats a warning already written.

        Parameters
        ----------
        record
            Record handed to the run log's file handler.

        Returns
        -------
        bool
            Whether the record is written.
        """
        # counted before a repeat is dropped, so the counts stay honest
        self.counts[record.levelname] += 1

        if record.levelno < logging.WARNING:
            return True

        message = record.getMessage()
        if message in self.seen:
            self.suppressed += 1
            return False

        self.seen.add(message)
        if len(self.digest) < _MAX_DIGEST_WARNINGS:
            self.digest.append(message)

        return True


class _RunLogFormatter(logging.Formatter):
    """Format a record as an entry of the run log."""

    def __init__(self) -> None:
        super().__init__(_LINE_FORMAT, datefmt=_TIME_FORMAT)

    @override
    def formatMessage(self, record: logging.LogRecord) -> str:
        """
        Format a record's entry, its message framed or extended as its extras ask.

        A record logged with ``extra={"heading": True}`` has its message framed in
        horizontal rules, and one with ``extra={"table": columns}``, values per
        column name, has the columns rendered as a table under its message. The
        line prefix stays outside both, and a traceback follows unframed.

        Parameters
        ----------
        record
            Record to format, its message already merged with its arguments.

        Returns
        -------
        str
            The entry, without its traceback.
        """
        message = record.message

        table = getattr(record, "table", None)
        if table is not None:
            message += "\n\n" + _render_table(table)

        if getattr(record, "heading", False):
            message = "\n" + _HLINE + "\n" + message + "\n" + _HLINE + "\n"

        # every handler formats the same record, so the entry is formatted from
        # the record's attributes rather than by writing the message back to it
        return _LINE_FORMAT % {**vars(record), "message": message}


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


def _render_table(columns: Mapping[str, Sequence[float]]) -> str:
    """
    Render columns of values as a table, each value rounded for display.

    Parameters
    ----------
    columns
        Values per column name, in column order; every column is equally long.

    Returns
    -------
    str
        The table in github format, without a trailing newline.
    """
    cells = [
        [str(_round_for_display(value)) for value in values]
        for values in columns.values()
    ]
    rows = list(zip(*cells, strict=True))
    table: str = tabulate(
        rows, headers=list(columns), tablefmt="github", stralign="right"
    )

    return table


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
