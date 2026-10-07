# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The run log of a CLI run and the console preamble.

The run log owns the log file, its line format, the warning ledger and the
end-of-run summary. The CLI in ``navigate.app.cli`` holds a ``RunLog`` open for
the whole run; the modules it runs log through their own module loggers.
"""

from __future__ import annotations

import logging
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Self, override

from tabulate import tabulate

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from types import TracebackType

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

_LINE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_TIME_FORMAT = "%H:%M:%S"
_HLINE = "=" * 120

_MAX_DIGEST_WARNINGS = 20
_MAX_DIGEST_LENGTH = 120

logger = logging.getLogger(__name__)


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
        if level not in LOG_LEVELS:
            raise ValueError(f"log level must be one of {LOG_LEVELS}, not {level!r}")

        self._log_path: Path = path.with_suffix(".log")
        self._level: str = level
        self._ledger: _WarningLedger = _WarningLedger()

        # set on entering
        self._handler: logging.FileHandler
        self._previous_level: int

    def __enter__(self) -> Self:
        # the file opens before the root logger changes, so a file that cannot be
        # opened leaves the logging configuration as it was
        handler = logging.FileHandler(self._log_path, mode="w", encoding="utf-8")
        handler.setFormatter(_RunLogFormatter())
        # propagation does not recheck the root's level, so the handler holds the
        # level for a logger that a host program has set lower
        handler.setLevel(self._level)
        # on the handler, the ledger sees every record at the run's level that
        # propagates from the module loggers
        handler.addFilter(self._ledger)

        # module loggers inherit their effective level from the root, so a record
        # below the run's level is not even created
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

    def log_summary(self) -> None:
        """Log the end-of-run summary: the record counts, then the unique warnings."""
        level_counts = self._ledger.level_counts
        warning_counts = self._ledger.warning_counts
        levels = LOG_LEVELS + [
            level for level in level_counts if level not in LOG_LEVELS
        ]

        # read before the summary is logged, so its own records are not counted
        table = {"Level": levels, "Count": [level_counts[level] for level in levels]}

        logger.info("Log summary:", extra={"table": table})

        if not warning_counts:
            return

        unique_count = len(warning_counts)

        logger.info(
            "Unique warnings (%d unique, %d duplicates suppressed):\n%s",
            unique_count,
            warning_counts.total() - unique_count,
            _list_warnings(warning_counts),
        )

    def print_warning_notice(self) -> None:
        """Print the number of warnings logged so far to the console, if any were."""
        warnings = self._ledger.level_counts["WARNING"]

        if warnings:
            print(f"{warnings} warning(s) logged - see '{self._log_path.name}'.")


class _WarningLedger(logging.Filter):
    """Count every record of a run per level, and drop repeats at WARNING and above."""

    def __init__(self) -> None:
        super().__init__()
        self.level_counts: Counter[str] = Counter()
        self.warning_counts: Counter[str] = Counter()

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
        self.level_counts[record.levelname] += 1

        if record.levelno < logging.WARNING:
            return True

        message = record.getMessage()
        self.warning_counts[message] += 1

        return self.warning_counts[message] == 1


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

        # every handler formats the same record, so the extended message goes
        # into the line format and the record keeps the message it was logged with
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


def _list_warnings(warning_counts: Counter[str]) -> str:
    """
    List the first unique warnings as numbered lines, each with its repeat count.

    Parameters
    ----------
    warning_counts
        Number of times each warning was logged, in the order first logged.

    Returns
    -------
    str
        One line per warning, and a closing line counting those left out.
    """
    lines = []
    first = islice(warning_counts.items(), _MAX_DIGEST_WARNINGS)

    for i, (message, count) in enumerate(first, 1):
        # the count leads, so truncating a long message never hides it
        times = f"({count}x) " if count > 1 else ""
        short = (
            message[:_MAX_DIGEST_LENGTH] + "..."
            if len(message) > _MAX_DIGEST_LENGTH
            else message
        )
        lines.append(f"  {i}. {times}{short}")

    if len(warning_counts) > _MAX_DIGEST_WARNINGS:
        lines.append(f"  ... and {len(warning_counts) - _MAX_DIGEST_WARNINGS} more")

    return "\n".join(lines)


def _render_table(columns: Mapping[str, Iterable[object]]) -> str:
    """
    Render columns of values as a table, with floats to three significant figures.

    Parameters
    ----------
    columns
        Values per column name, in column order; every column is equally long.

    Returns
    -------
    str
        The table in github format, without a trailing newline.
    """
    rows = list(zip(*columns.values(), strict=True))
    table: str = tabulate(
        rows,
        headers=list(columns),
        tablefmt="github",
        stralign="right",
        floatfmt=".3g",
    )

    return table
