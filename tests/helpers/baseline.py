# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Golden-baseline comparison and regeneration over report CSV output.

The baseline artifact is the CSV output of a deck's Report node, committed
under the regression suite's baselines/ directory. Files pair by name, columns
by header token and rows by their Date cell, and cells compare exactly unless
the deck opts into a tolerance. Conventions: tests/regression/README.md.
"""

from __future__ import annotations

import csv
import math
import re
import shutil
from collections import Counter
from typing import TYPE_CHECKING

from helpers.simulation import check_invariants

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from navigate.simulation import SimulationManager

# runner-noise floor, opted into per deck (the comparison default stays exact).
# Pinning the solver backend fixes neither its thread count nor the CPU dispatch
# in its float kernels, so an LP with non-unique optima can resolve ties
# differently from one machine to the next: nonzero cells drift by a few parts
# in 1e14, and degenerate ties move between adjacent year bins, which lifts
# exact-zero cells to ~1e-11. rtol covers the first regime at ~18x headroom over
# the worst drift observed; atol is the only guard on the second, and on the
# exact-zero cells that encode a gated-off pathway, where 1e-9 is inert in every
# unit the report carries - vessels, MW, USD and dimensionless fractions.
RUNNER_NOISE_RTOL = 1e-12
RUNNER_NOISE_ATOL = 1e-9

# The report writer dodges a locked target file by writing to "<name> (1).csv"
# instead of failing; such a file must never be compared or become a baseline.
_RETRY_NAME = re.compile(r" \(\d+\)\.csv$")

_DATE_COLUMN = "Date"

# differences listed in a failure message; the count is always given in full
_MAX_LISTED = 50

_REGEN_HINT = (
    "If this change is intended: regenerate with `make regen-regression`, "
    "review the baseline git diff against what the change was meant to do, "
    "and commit it as its own commit. tests/regression/README.md has the "
    "triage steps for a red suite."
)


def regen_or_compare(
    manager: SimulationManager,
    baseline_dir: Path,
    output_dir: Path,
    *,
    regen: bool,
    check_activation: Callable[[SimulationManager], None],
    rtol: float = 0.0,
    atol: float = 0.0,
) -> None:
    """
    Compare against the baselines, or regenerate them: every deck's golden test body.

    Regeneration (the suite's --regen-baselines flag) runs the universal
    invariants and the deck's activation guards before replacing anything, so a
    deck whose mechanism stopped firing cannot regenerate, even when its golden
    test is targeted directly. rtol and atol are those of compare_baselines.
    """
    if regen:
        check_invariants(manager)
        check_activation(manager)
        copied = regen_baselines(baseline_dir, output_dir)
        print(f"regenerated {len(copied)} baseline file(s): {', '.join(copied)}")
        return

    diffs = compare_baselines(baseline_dir, output_dir, rtol=rtol, atol=atol)
    if diffs:
        listed = diffs[:_MAX_LISTED]
        if len(diffs) > len(listed):
            listed.append(f"... and {len(diffs) - len(listed)} more")
        summary = f"Golden-baseline comparison failed: {len(diffs)} difference(s)"
        raise AssertionError("\n".join([summary, *listed, _REGEN_HINT]))


def compare_baselines(
    baseline_dir: Path, output_dir: Path, *, rtol: float = 0.0, atol: float = 0.0
) -> list[str]:
    """
    List every difference between a run's report CSVs and the baselines, one per line.

    A numeric cell passes iff ``abs(actual - baseline) <= atol + rtol *
    abs(baseline)``. Exact by default; a nonzero tolerance requires recorded
    evidence (see the suite README).
    """
    baseline_names = _csv_names(baseline_dir)
    output_names = _csv_names(output_dir)

    diffs = [
        f"{name}: missing from run" for name in sorted(baseline_names - output_names)
    ]
    diffs += [
        f"{name}: not in baseline" for name in sorted(output_names - baseline_names)
    ]

    for name in sorted(baseline_names & output_names):
        baseline = _load_csv(baseline_dir / name)
        actual = _load_csv(output_dir / name)
        baseline_columns = _columns(baseline)
        actual_columns = _columns(actual)

        for label, missing in (
            ("column missing from run", baseline_columns - actual_columns),
            ("column not in baseline", actual_columns - baseline_columns),
            ("date missing from run", baseline.keys() - actual.keys()),
            ("date not in baseline", actual.keys() - baseline.keys()),
        ):
            diffs += [f"{name}: {label}: {item}" for item in sorted(missing)]

        # rows pair by date and cells by column name, so a shifted horizon or a
        # reordered header still compares the values the two runs share
        for date in sorted(baseline.keys() & actual.keys()):
            for column in sorted(baseline_columns & actual_columns):
                expected = baseline[date][column]
                found = actual[date][column]
                if not cells_equal(expected, found, rtol, atol):
                    diffs.append(
                        f"{name} :: {column} @ {date}: "
                        f"baseline={expected} actual={found}"
                    )

    return diffs


def cells_equal(baseline: str, actual: str, rtol: float, atol: float) -> bool:
    """
    Whether two report cells match within tolerance.

    Cells that parse as floats compare numerically. NaN equals NaN and an
    infinity equals only the same-sign infinity: the report writer emits both
    as deterministic tokens, and the tolerance formula would call them unequal.
    Anything else compares as exact text.
    """
    try:
        expected = float(baseline)
        found = float(actual)
    except ValueError:
        return baseline == actual

    if math.isnan(expected) or math.isnan(found):
        return math.isnan(expected) and math.isnan(found)
    if math.isinf(expected) or math.isinf(found):
        return expected == found
    return abs(found - expected) <= atol + rtol * abs(expected)


def regen_baselines(baseline_dir: Path, output_dir: Path) -> list[str]:
    """
    Replace the baselines with the run's report CSVs; return the copied names.

    The output is validated before anything is deleted, and the copy is
    delete-then-copy, so a sheet that disappeared shows up as a deletion in the
    git diff instead of lingering.
    """
    names = sorted(_csv_names(output_dir))
    if not names:
        raise ValueError(
            f"{output_dir} contains no report CSVs: nothing to promote to "
            "baselines (did the deck's Report node run?)"
        )
    for name in names:
        _load_csv(output_dir / name)

    shutil.rmtree(baseline_dir, ignore_errors=True)
    baseline_dir.mkdir(parents=True)
    for name in names:
        shutil.copyfile(output_dir / name, baseline_dir / name)

    return names


def _csv_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    names = {path.name for path in directory.glob("*.csv")}
    retries = sorted(name for name in names if _RETRY_NAME.search(name))
    if retries:
        raise ValueError(
            f"{directory} contains locked-file retry output "
            f"({', '.join(retries)}): a file was locked while the report "
            "writer ran. Close whatever holds it and rerun."
        )
    return names


def _columns(data: dict[str, dict[str, str]]) -> set[str]:
    # every row of a loaded CSV carries the same header
    return set(next(iter(data.values()), ()))


def _load_csv(path: Path) -> dict[str, dict[str, str]]:
    """
    Load one report CSV as ``{date: {column: cell}}``.

    Rejects duplicate header tokens and duplicate dates: both would make
    name-based cell pairing ambiguous (a duplicate header typically means a
    property was requested both through a wildcard and explicitly).
    """
    with path.open(newline="") as file:
        rows = list(csv.reader(file))

    if not rows or _DATE_COLUMN not in rows[0]:
        raise ValueError(f"{path} is not a report CSV (no '{_DATE_COLUMN}' column)")

    header = rows[0]
    duplicates = sorted(name for name, count in Counter(header).items() if count > 1)
    if duplicates:
        raise ValueError(f"{path} has duplicate columns: {', '.join(duplicates)}")

    date_idx = header.index(_DATE_COLUMN)
    data: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        date = row[date_idx]
        if date in data:
            raise ValueError(f"{path} has duplicate date rows: {date}")
        data[date] = {
            name: cell
            for name, cell in zip(header, row, strict=True)
            if name != _DATE_COLUMN
        }
    return data
