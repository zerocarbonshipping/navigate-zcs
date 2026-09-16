# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Golden-baseline comparison and regeneration over report CSV output.

The baseline artifact is the CSV output of a deck's Report node, committed
under the regression suite's baselines/ directory. Comparison is structural
first (file sets, header sets, date sets), then cell-by-cell with an exact
default (rtol = atol = 0); every failure is reported as a structured diff,
never a bare pass/fail. Conventions: tests/regression/README.md.
"""

from __future__ import annotations

import csv
import math
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
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

_REGEN_HINT = (
    "If this change is intended: regenerate with `make regen-regression`, "
    "review the baseline git diff, and commit it as its own commit. Triage "
    '"different and correct" vs "different and broken" against '
    "tests/guardrails (see tests/regression/README.md)."
)

# (field name, report label) — ok(), the summary line, and the report body
# all derive from this one table
_STRUCTURAL_FIELDS = (
    ("missing_files", "files missing from run"),
    ("extra_files", "files not in baseline"),
    ("missing_columns", "columns missing from run"),
    ("extra_columns", "columns not in baseline"),
    ("missing_dates", "dates missing from run"),
    ("extra_dates", "dates not in baseline"),
)


@dataclass(frozen=True)
class ValueDiff:
    """One differing cell between a baseline CSV and a run CSV."""

    file: str  # CSV filename, identifying the report sheet
    column: str  # header token, e.g. "node.attribute.key"
    date: str  # the row's Date cell
    baseline: str  # raw baseline cell text
    actual: str  # raw run cell text
    abs_dev: float  # absolute deviation; inf for non-numeric mismatches
    rel_dev: float  # deviation over the larger magnitude; inf sorts first


@dataclass
class ComparisonResult:
    """Structured outcome of one baseline-vs-run comparison."""

    missing_files: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    missing_columns: dict[str, list[str]] = field(default_factory=dict)
    extra_columns: dict[str, list[str]] = field(default_factory=dict)
    missing_dates: dict[str, list[str]] = field(default_factory=dict)
    extra_dates: dict[str, list[str]] = field(default_factory=dict)
    value_diffs: list[ValueDiff] = field(default_factory=list)
    cells_compared: int = 0

    def ok(self) -> bool:
        """Whether the run matches the baseline within tolerance (no diffs at all)."""
        return not (
            self.value_diffs
            or any(getattr(self, name) for name, _ in _STRUCTURAL_FIELDS)
        )

    def format(self, top_n: int = 20) -> str:
        """
        Render the diff as a readable failure report.

        Parameters
        ----------
        top_n
            Maximum number of value diffs to list, largest relative
            deviation first.
        """
        lines = [self._summary_line(), ""]

        structural = self._structural_lines()
        if structural:
            lines.append("Structural differences:")
            lines.extend(structural)
            lines.append("")

        if self.value_diffs:
            diffs = sorted(
                self.value_diffs, key=lambda d: (d.rel_dev, d.abs_dev), reverse=True
            )
            lines.append(
                f"Largest value diffs (showing {min(top_n, len(diffs))} "
                f"of {len(diffs)}):"
            )
            lines.extend(
                f"  {d.file} :: {d.column} @ {d.date}: "
                f"baseline={d.baseline} actual={d.actual} "
                f"(rel {d.rel_dev:.3e}, abs {d.abs_dev:.3e})"
                for d in diffs[:top_n]
            )
            lines.append("")

        lines.append(_REGEN_HINT)
        return "\n".join(lines)

    def _summary_line(self) -> str:
        files_affected = {diff.file for diff in self.value_diffs}
        for name, _ in _STRUCTURAL_FIELDS:
            files_affected.update(getattr(self, name))
        summary = (
            f"Golden-baseline comparison failed: {len(self.value_diffs)} "
            f"differing cell(s) of {self.cells_compared} compared, "
            f"{len(files_affected)} file(s) affected."
        )
        if self.value_diffs:
            max_rel = max(diff.rel_dev for diff in self.value_diffs)
            max_abs = max(diff.abs_dev for diff in self.value_diffs)
            summary += f" Max rel dev {max_rel:.3e}, max abs dev {max_abs:.3e}."
        return summary

    def _structural_lines(self) -> list[str]:
        lines = []
        for name, label in _STRUCTURAL_FIELDS:
            value = getattr(self, name)
            if isinstance(value, dict):
                lines.extend(
                    f"  {file}: {label}: {', '.join(items)}"
                    for file, items in value.items()
                )
            elif value:
                lines.append(f"  {label}: {', '.join(value)}")
        return lines


def regen_or_compare(
    manager: SimulationManager,
    baseline_dir: Path,
    output_dir: Path,
    *,
    regen: bool,
    check_activation: Callable[[SimulationManager], None],
    rtol: float = 0.0,
    atol: float = 0.0,
    exclude_columns: tuple[str, ...] = (),
) -> None:
    """
    Compare against the baselines, or regenerate them — every deck's golden test body.

    Regeneration re-runs the universal invariants and the deck's activation
    guards before replacing anything, so the guard-before-regen ordering is
    mechanical for every deck — a vacuous baseline cannot be regenerated even
    by targeting one deck's golden test directly.

    Parameters
    ----------
    manager
        Manager of the deck's completed run.
    baseline_dir
        Directory holding the committed baseline CSVs.
    output_dir
        The deck's report output directory from the run.
    regen
        The suite's --regen-baselines flag.
    check_activation
        The deck module's activation guards.
    rtol, atol, exclude_columns
        Passed to the comparison; see compare_baselines.
    """
    if regen:
        check_invariants(manager)
        check_activation(manager)
        copied = regen_baselines(baseline_dir, output_dir)
        print(f"regenerated {len(copied)} baseline file(s): {', '.join(copied)}")
    else:
        assert_matches_baseline(
            baseline_dir,
            output_dir,
            rtol=rtol,
            atol=atol,
            exclude_columns=exclude_columns,
        )


def compare_baselines(
    baseline_dir: Path,
    output_dir: Path,
    *,
    rtol: float = 0.0,
    atol: float = 0.0,
    exclude_columns: tuple[str, ...] = (),
) -> ComparisonResult:
    """
    Compare a run's report CSVs against the committed baseline CSVs.

    Parameters
    ----------
    baseline_dir
        Directory holding the committed baseline CSVs.
    output_dir
        The deck's report output directory from the run under test.
    rtol, atol
        Cell tolerance: a cell passes iff
        ``abs(actual - baseline) <= atol + rtol * abs(baseline)``. Exact by
        default; a nonzero value requires recorded evidence (see the suite
        README).
    exclude_columns
        Exact header tokens excluded from comparison entirely (presence and
        value) — no wildcards, so an exclusion can never silently widen.
        Every use requires an evidence comment at the call site.

    Returns
    -------
    The structured diff; empty (``ok()``) when the run matches.
    """
    baseline_names = _csv_names(baseline_dir)
    output_names = _csv_names(output_dir)
    _reject_retry_names(output_dir, output_names)
    _reject_retry_names(baseline_dir, baseline_names)

    result = ComparisonResult(
        missing_files=sorted(baseline_names - output_names),
        extra_files=sorted(output_names - baseline_names),
    )

    for name in sorted(baseline_names & output_names):
        _compare_file(
            result,
            name,
            _load_csv(baseline_dir / name),
            _load_csv(output_dir / name),
            rtol,
            atol,
            exclude_columns,
        )

    return result


def assert_matches_baseline(
    baseline_dir: Path,
    output_dir: Path,
    *,
    rtol: float = 0.0,
    atol: float = 0.0,
    exclude_columns: tuple[str, ...] = (),
    top_n: int = 20,
) -> None:
    """
    Assert a run's report CSVs match the committed baselines.

    Raises AssertionError carrying the full structured diff report on any
    mismatch; parameters are those of ``compare_baselines``.
    """
    result = compare_baselines(
        baseline_dir,
        output_dir,
        rtol=rtol,
        atol=atol,
        exclude_columns=exclude_columns,
    )
    if not result.ok():
        raise AssertionError(result.format(top_n))


def regen_baselines(baseline_dir: Path, output_dir: Path) -> list[str]:
    """
    Replace the committed baselines with the current run's report CSVs.

    Delete-then-copy, so sheets or columns that disappeared show up as
    deletions in the git diff instead of lingering. The output is validated
    (present at all, retry names, duplicate headers) before anything is
    deleted.

    Returns
    -------
    The copied filenames, sorted.
    """
    names = sorted(_csv_names(output_dir))
    if not names:
        raise ValueError(
            f"{output_dir} contains no report CSVs — nothing to promote to "
            "baselines (did the deck's Report node run?)"
        )
    _reject_retry_names(output_dir, names)
    for name in names:
        _load_csv(output_dir / name)  # validates headers and dates

    shutil.rmtree(baseline_dir, ignore_errors=True)
    baseline_dir.mkdir(parents=True)
    for name in names:
        shutil.copyfile(output_dir / name, baseline_dir / name)

    return names


def _csv_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {path.name for path in directory.glob("*.csv")}


def _reject_retry_names(directory: Path, names: list[str] | set[str]) -> None:
    retries = sorted(name for name in names if _RETRY_NAME.search(name))
    if retries:
        raise ValueError(
            f"{directory} contains locked-file retry output "
            f"({', '.join(retries)}): a file was locked while the report "
            "writer ran. Close whatever holds it and rerun."
        )


def _load_csv(path: Path) -> dict[str, dict[str, str]]:
    """
    Load one report CSV as ``{date: {column: cell}}``.

    Rejects duplicate header tokens and duplicate dates: both would make
    name-based cell pairing ambiguous (a duplicate header typically means a
    property was requested both via a node wildcard and explicitly).
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
    data = {}
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


def _compare_file(
    result: ComparisonResult,
    name: str,
    baseline: dict[str, dict[str, str]],
    actual: dict[str, dict[str, str]],
    rtol: float,
    atol: float,
    exclude_columns: tuple[str, ...],
) -> None:
    baseline_columns = _included_columns(baseline, exclude_columns)
    actual_columns = _included_columns(actual, exclude_columns)

    if missing := sorted(baseline_columns - actual_columns):
        result.missing_columns[name] = missing
    if extra := sorted(actual_columns - baseline_columns):
        result.extra_columns[name] = extra

    if missing := sorted(set(baseline) - set(actual)):
        result.missing_dates[name] = missing
    if extra := sorted(set(actual) - set(baseline)):
        result.extra_dates[name] = extra

    columns = sorted(baseline_columns & actual_columns)
    for date in sorted(baseline.keys() & actual.keys()):
        for column in columns:
            result.cells_compared += 1
            deviation = _cell_deviation(
                baseline[date][column], actual[date][column], rtol, atol
            )
            if deviation is not None:
                abs_dev, rel_dev = deviation
                result.value_diffs.append(
                    ValueDiff(
                        name,
                        column,
                        date,
                        baseline[date][column],
                        actual[date][column],
                        abs_dev,
                        rel_dev,
                    )
                )


def _included_columns(
    data: dict[str, dict[str, str]], exclude_columns: tuple[str, ...]
) -> set[str]:
    # every row of a loaded CSV carries the same header, so any row's keys
    # are the file's columns
    columns = set(next(iter(data.values()), ()))
    return columns - set(exclude_columns)


def _cell_deviation(
    baseline: str, actual: str, rtol: float, atol: float
) -> tuple[float, float] | None:
    """
    Deviation of one cell pair as ``(abs_dev, rel_dev)``, or None when equal.

    Cells that parse as floats compare numerically: NaN equals NaN and
    same-sign infinities are equal (the report writer emits both as
    deterministic tokens; the bare formula would misreport them), while
    NaN-vs-number and cross-sign infinities report an infinite deviation.
    Anything else compares as exact text.
    """
    try:
        baseline_value = float(baseline)
        actual_value = float(actual)
    except ValueError:
        return None if baseline == actual else (math.inf, math.inf)

    if baseline_value == actual_value:
        return None
    if math.isnan(baseline_value) and math.isnan(actual_value):
        return None

    abs_dev = abs(actual_value - baseline_value)
    if not math.isfinite(abs_dev):
        return (math.inf, math.inf)
    if abs_dev <= atol + rtol * abs(baseline_value):
        return None

    rel_dev = abs_dev / max(abs(baseline_value), abs(actual_value))
    return (abs_dev, rel_dev)
