# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the golden-baseline comparison utility.

The oracle is the comparison contract stated in helpers/baseline.py: NaN equals
NaN, an infinity equals only the same-sign infinity, rows pair by date, and
invalid artifacts are rejected outright.
"""

from __future__ import annotations

import pytest

from helpers.baseline import cells_equal, compare_baselines


def write_csv(directory, name, header, rows):
    directory.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)] + [",".join(row) for row in rows]
    (directory / name).write_text("\n".join(lines) + "\n")


@pytest.mark.parametrize(
    ("baseline", "actual", "equal"),
    [
        ("nan", "nan", True),
        ("inf", "inf", True),
        ("-0.0", "0.0", True),  # not a result change
        ("nan", "1.0", False),
        ("inf", "-inf", False),
        ("inf", "1.0", False),
    ],
)
# exact, and wide enough that the bare tolerance formula would pass inf vs 1.0
@pytest.mark.parametrize("tolerance", [0.0, 1.0])
def test_cells_equal(baseline, actual, equal, tolerance):
    assert cells_equal(baseline, actual, rtol=tolerance, atol=tolerance) is equal


def test_dates_pair_by_value_not_position(tmp_path):
    # a shifted horizon must not misalign the overlapping rows: the value
    # change on the shared date is reported alongside the date differences
    baselines, output = tmp_path / "baselines", tmp_path / "output"
    write_csv(baselines, "f.csv", ["Date", "a"], [["d1", "1"], ["d2", "2"]])
    write_csv(output, "f.csv", ["Date", "a"], [["d2", "9"], ["d3", "3"]])

    assert compare_baselines(baselines, output) == [
        "f.csv: date missing from run: d1",
        "f.csv: date not in baseline: d3",
        "f.csv :: a @ d2: baseline=2 actual=9",
    ]


@pytest.mark.parametrize(
    ("name", "header", "match"),
    [
        ("f.csv", ["Date", "a", "a"], "duplicate columns: a"),
        ("f (1).csv", ["Date", "a"], "locked-file retry"),
    ],
)
def test_invalid_artifacts_rejected(tmp_path, name, header, match):
    baselines, output = tmp_path / "baselines", tmp_path / "output"
    write_csv(baselines, "f.csv", ["Date", "a"], [["d1", "1"]])
    write_csv(output, name, header, [["d1"] + ["1"] * (len(header) - 1)])

    with pytest.raises(ValueError, match=match):
        compare_baselines(baselines, output)
