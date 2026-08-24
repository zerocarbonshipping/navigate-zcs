# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import time as time_module
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from tabulate import tabulate

from navigate.core.unit import YEAR_TO_DAYS
from navigate.util import round_for_display

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
HLINE = '=' * 120
_COUNT_HANDLER = None
_DEDUP_FILTER = None
_WALL_START_TIME = None

_MAX_DIGEST_WARNINGS = 20


class _DeduplicatingFilter(logging.Filter):
    """Suppress duplicate WARNING+ messages in the file log.

    The first occurrence passes through; subsequent identical messages
    are counted but not written. INFO and DEBUG always pass.
    """

    def __init__(self):
        super().__init__()
        self._seen: set = set()
        self.suppressed: int = 0
        self.unique_warnings: list = []

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.WARNING:
            return True
        key = record.getMessage()
        if key in self._seen:
            self.suppressed += 1
            return False
        self._seen.add(key)
        if len(self.unique_warnings) < _MAX_DIGEST_WARNINGS:
            self.unique_warnings.append(key)
        return True


def setup_logger(path: str, level=logging.INFO) -> logging.Logger:

    filename = os.path.splitext(path)[0] + '.log'
    file_handler = logging.FileHandler(filename, mode="w")

    class _CountingHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.counter = Counter()

        def emit(self, record: logging.LogRecord) -> None:
            self.counter[record.levelname] += 1

    global _COUNT_HANDLER, _DEDUP_FILTER
    _COUNT_HANDLER = _CountingHandler()
    _DEDUP_FILTER = _DeduplicatingFilter()

    # Dedup filter on file handler only; counting handler sees all records
    file_handler.addFilter(_DEDUP_FILTER)

    logging.basicConfig(level=level,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        datefmt="%H:%M:%S",
                        handlers=[file_handler, _COUNT_HANDLER],
                        force=True)

    return logging.getLogger()


def print_preamble():
    try:
        pkg_version = version('navigate-zcs')
    except PackageNotFoundError:
        pkg_version = 'Debug'

    file = Path(__file__).parent / 'preamble.txt'
    with open(file, 'r') as f:
        preamble = f.read()
    print(preamble.format(pkg_version))


def log_time_step_breaker(logger, idx, date, time):
    elapsed_time = time_module.perf_counter() - _WALL_START_TIME if _WALL_START_TIME else 0
    msg = (
        f"Time-step: {idx}, current date: {date}. "
        f"{int(time)} days "
        f"({int(round(time / YEAR_TO_DAYS, 0))} years) "
        "since start of simulation. "
        f"Wall time since start: {elapsed_time:,.1f} s"
    )
    logger.info(_wrap_in_hlines(msg))


def log_extrapolate_bounds(logger, node, x, a, b):
    info = f' Value was {x}.' if x.size < 5 else ''
    logger.warning(f"{node}: Extrapolating beyond table limits ({a}, {b}).{info}")


def log_start_of_simulation(logger, date):
    global _WALL_START_TIME
    _WALL_START_TIME = time_module.perf_counter()
    logger.info(_wrap_in_hlines(f"Time-step: 0, starting simulation at date: {date}"))


def log_model_post_process(logger):
    logger.info(_wrap_in_hlines("Post-process model after end of simulation"))


def log_fair_share_convergence(logger, statistics, iterations, converged) -> None:
    headers = ["Iter."] + list(statistics.keys())
    cols = list(statistics.values())
    rows = [[i + 1] + [str(round_for_display(cols[c][i])) for c in range(len(cols))]
            for i in range(iterations)]

    table = tabulate(rows, headers=headers, tablefmt="github", stralign="right")

    if converged:
        logger.info("Fair-share bunkering convergence status: Successful.")
        logger.debug("Fair-share bunkering convergence statistics:\n\n%s", table)
    else:
        msg = "Fair-share bunkering convergence status: Failure.\n"
        msg += f"Fair-share bunkering convergence statistics:\n\n{table}"
        logger.info(msg)


def _wrap_in_hlines(msg):
    return '\n' + HLINE + '\n' + msg + '\n' + HLINE + '\n'


def get_log_counts() -> dict:
    if not _COUNT_HANDLER:
        return {}
    return {lvl: _COUNT_HANDLER.counter.get(lvl, 0)
            for lvl in set(LOG_LEVELS) | set(_COUNT_HANDLER.counter)}


def log_summary() -> str:
    counts = get_log_counts()

    rows = [[lvl, counts.get(lvl, 0)] for lvl in LOG_LEVELS
            if lvl in counts] + [[lvl, counts[lvl]] for lvl in counts if lvl not in LOG_LEVELS]
    table = tabulate(rows, headers=["Level", "Count"], tablefmt="github", stralign="right")

    summary = f"\nLog summary:\n{table}"

    # Append warning digest from dedup filter
    if _DEDUP_FILTER and _DEDUP_FILTER.unique_warnings:
        n_unique = len(_DEDUP_FILTER._seen)
        n_suppressed = _DEDUP_FILTER.suppressed
        summary += f"\n\nUnique warnings ({n_unique} unique, {n_suppressed} duplicates suppressed):"
        for i, msg in enumerate(_DEDUP_FILTER.unique_warnings, 1):
            # Truncate long messages for the digest
            short = (msg[:120] + '...') if len(msg) > 120 else msg
            summary += f"\n  {i}. {short}"
        if n_unique > _MAX_DIGEST_WARNINGS:
            summary += f"\n  ... and {n_unique - _MAX_DIGEST_WARNINGS} more"

    return summary
