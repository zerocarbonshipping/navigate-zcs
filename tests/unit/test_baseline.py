# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the golden-baseline comparison utility.

The oracle is the comparison contract stated in helpers/baseline.py: exact by
default, NaN equals NaN, same-sign infinities are equal, structural
differences (files, columns, dates) are reported by name, and invalid
artifacts (retry names, duplicate headers) are rejected outright.
"""

from __future__ import annotations

import math

import pytest

import helpers.baseline
from helpers.baseline import (
    ValueDiff,
    _cell_deviation,
    assert_matches_baseline,
    compare_baselines,
    regen_baselines,
    regen_or_compare,
)


def write_csv(directory, name, header, rows):
    directory.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)] + [",".join(str(c) for c in row) for row in rows]
    (directory / name).write_text("\n".join(lines) + "\n")


@pytest.fixture
def dirs(tmp_path):
    return tmp_path / "baselines", tmp_path / "output"


class TestCellDeviation:
    @pytest.mark.parametrize(
        ("baseline", "actual"),
        [
            ("1.5", "1.5"),
            ("1.5", "1.50"),  # same parsed value, different text
            ("-0.0", "0.0"),  # not a result change
            ("nan", "nan"),
            ("inf", "inf"),
            ("-inf", "-inf"),
            ("text", "text"),  # non-numeric falls back to text equality
        ],
    )
    def test_equal(self, baseline, actual):
        assert _cell_deviation(baseline, actual, 0.0, 0.0) is None

    @pytest.mark.parametrize(
        ("baseline", "actual"),
        [
            ("nan", "1.0"),  # NaN vs number
            ("1.0", "nan"),
            ("inf", "-inf"),  # cross-sign infinities
            ("inf", "1.0"),
            ("text", "other"),  # non-numeric mismatch
        ],
    )
    def test_infinite_deviation(self, baseline, actual):
        assert _cell_deviation(baseline, actual, 0.0, 0.0) == (math.inf, math.inf)

    def test_exact_by_default(self):
        deviation = _cell_deviation("1.0", "1.0000000000000002", 0.0, 0.0)
        assert deviation is not None
        abs_dev, rel_dev = deviation
        assert abs_dev == pytest.approx(2.2e-16, rel=0.1)
        assert rel_dev == pytest.approx(2.2e-16, rel=0.1)

    @pytest.mark.parametrize(
        ("rtol", "atol", "equal"),
        [
            (0.0, 0.0, False),
            (0.011, 0.0, True),  # abs(2.02 - 2.0) <= rtol * 2.0
            (0.009, 0.0, False),
            (0.0, 0.021, True),  # abs(2.02 - 2.0) <= atol
            (0.0, 0.019, False),
        ],
    )
    def test_tolerance_formula(self, rtol, atol, equal):
        deviation = _cell_deviation("2.0", "2.02", rtol, atol)
        assert (deviation is None) == equal

    def test_relative_deviation_uses_larger_magnitude(self):
        deviation = _cell_deviation("1.0", "4.0", 0.0, 0.0)
        assert deviation == (3.0, 0.75)


class TestCompareBaselines:
    def test_identical(self, dirs):
        baselines, output = dirs
        for directory in dirs:
            write_csv(
                directory,
                "deck_report_Global.csv",
                ["Date", "Time (days)", "a.b"],
                [["2026-01-01", "0.0", "1.5"], ["2027-01-01", "365.0", "2.5"]],
            )

        result = compare_baselines(baselines, output)

        assert result.ok()
        assert result.cells_compared == 4

    def test_missing_and_extra_files(self, dirs):
        baselines, output = dirs
        write_csv(baselines, "deck_report_Global.csv", ["Date", "a"], [["d1", "1"]])
        write_csv(output, "deck_report_Fleets.csv", ["Date", "a"], [["d1", "1"]])

        result = compare_baselines(baselines, output)

        assert result.missing_files == ["deck_report_Global.csv"]
        assert result.extra_files == ["deck_report_Fleets.csv"]
        assert not result.ok()

    def test_missing_and_extra_columns_by_name(self, dirs):
        baselines, output = dirs
        write_csv(baselines, "f.csv", ["Date", "a", "b"], [["d1", "1", "2"]])
        write_csv(output, "f.csv", ["Date", "b", "c"], [["d1", "2", "3"]])

        result = compare_baselines(baselines, output)

        assert result.missing_columns == {"f.csv": ["a"]}
        assert result.extra_columns == {"f.csv": ["c"]}
        # the shared column is still compared despite the structural diff
        assert result.cells_compared == 1
        assert not result.value_diffs

    def test_dates_pair_by_value_not_position(self, dirs):
        # a shifted horizon must not misalign the overlapping rows: the value
        # regression on the shared date is reported alongside the date diff
        baselines, output = dirs
        write_csv(baselines, "f.csv", ["Date", "a"], [["d1", "1"], ["d2", "2"]])
        write_csv(output, "f.csv", ["Date", "a"], [["d2", "9"], ["d3", "3"]])

        result = compare_baselines(baselines, output)

        assert result.missing_dates == {"f.csv": ["d1"]}
        assert result.extra_dates == {"f.csv": ["d3"]}
        assert result.value_diffs == [
            ValueDiff("f.csv", "a", "d2", "2", "9", 7.0, 7.0 / 9.0)
        ]

    def test_exclude_columns_covers_presence_and_value(self, dirs):
        baselines, output = dirs
        write_csv(baselines, "f.csv", ["Date", "keep", "x.skip"], [["d1", "1", "2"]])
        write_csv(output, "f.csv", ["Date", "keep"], [["d1", "1"]])

        result = compare_baselines(baselines, output, exclude_columns=("x.skip",))

        assert result.ok()
        assert result.cells_compared == 1

    def test_exclude_columns_are_exact_tokens(self, dirs):
        # an exclusion must never silently widen to similar column names
        baselines, output = dirs
        write_csv(baselines, "f.csv", ["Date", "x.skip", "xxskip"], [["d1", "1", "1"]])
        write_csv(output, "f.csv", ["Date", "x.skip", "xxskip"], [["d1", "2", "2"]])

        result = compare_baselines(baselines, output, exclude_columns=("x.skip",))

        assert [diff.column for diff in result.value_diffs] == ["xxskip"]

    @pytest.mark.parametrize("invalid_side", [0, 1], ids=["baselines", "output"])
    @pytest.mark.parametrize(
        ("name", "header", "match"),
        [
            ("f.csv", ["Date", "a", "a"], "duplicate columns: a"),
            ("f (1).csv", ["Date", "a"], "locked-file retry"),
        ],
    )
    def test_invalid_artifacts_rejected(self, dirs, invalid_side, name, header, match):
        cells = ["1"] * (len(header) - 1)
        write_csv(dirs[1 - invalid_side], "f.csv", ["Date", "a"], [["d1", "1"]])
        write_csv(dirs[invalid_side], name, header, [["d1", *cells]])

        with pytest.raises(ValueError, match=match):
            compare_baselines(*dirs)

    def test_missing_baseline_dir_reports_extra_files(self, dirs):
        # first-ever run: everything is "not in baseline", pointing at regen
        baselines, output = dirs
        write_csv(output, "f.csv", ["Date", "a"], [["d1", "1"]])

        result = compare_baselines(baselines, output)

        assert result.extra_files == ["f.csv"]


class TestAssertMatchesBaseline:
    def test_report_names_the_diff_and_the_regen_command(self, dirs):
        baselines, output = dirs
        write_csv(baselines, "f.csv", ["Date", "node.attr"], [["d1", "1.0"]])
        write_csv(output, "f.csv", ["Date", "node.attr"], [["d1", "2.0"]])

        with pytest.raises(AssertionError) as excinfo:
            assert_matches_baseline(baselines, output)

        report = str(excinfo.value)
        assert "f.csv :: node.attr @ d1: baseline=1.0 actual=2.0" in report
        assert "make regen-regression" in report

    def test_report_sorts_by_relative_deviation_and_truncates(self, dirs):
        baselines, output = dirs
        write_csv(baselines, "f.csv", ["Date", "a", "b", "c"], [["d1", "1", "1", "1"]])
        write_csv(output, "f.csv", ["Date", "a", "b", "c"], [["d1", "1.1", "3", "2"]])

        with pytest.raises(AssertionError) as excinfo:
            assert_matches_baseline(baselines, output, top_n=2)

        report = str(excinfo.value)
        assert "3 differing cell(s) of 3 compared" in report
        assert "showing 2 of 3" in report
        # b (rel 2/3) before c (rel 1/2); a (rel ~0.09) truncated away
        assert report.index(":: b @") < report.index(":: c @")
        assert ":: a @" not in report


class TestRegenBaselines:
    def test_delete_then_copy(self, dirs):
        baselines, output = dirs
        write_csv(baselines, "stale.csv", ["Date", "a"], [["d1", "1"]])
        write_csv(output, "fresh.csv", ["Date", "a"], [["d1", "1"]])

        copied = regen_baselines(baselines, output)

        assert copied == ["fresh.csv"]
        assert not (baselines / "stale.csv").exists()
        assert (baselines / "fresh.csv").read_text() == (
            output / "fresh.csv"
        ).read_text()

    @pytest.mark.parametrize(
        ("name", "header", "match"),
        [
            ("f (1).csv", ["Date", "a"], "locked-file retry"),
            ("f.csv", ["Date", "a", "a"], "duplicate columns"),
            (None, None, "no report CSVs"),  # empty output directory
        ],
    )
    def test_invalid_output_leaves_baselines_untouched(self, dirs, name, header, match):
        baselines, output = dirs
        write_csv(baselines, "keep.csv", ["Date", "a"], [["d1", "1"]])
        if name is not None:
            write_csv(output, name, header, [["d1"] + ["1"] * (len(header) - 1)])

        with pytest.raises(ValueError, match=match):
            regen_baselines(baselines, output)

        assert (baselines / "keep.csv").exists()


class TestRegenOrCompare:
    """
    The guard-before-regen ordering contract.

    Invariants and activation guards run and pass before anything is
    replaced; comparison mode never calls them.
    """

    @pytest.fixture
    def quiet_invariants(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            helpers.baseline,
            "check_invariants",
            lambda manager: calls.append("invariants"),
        )
        return calls

    def test_regen_runs_guards_before_replacing(self, dirs, quiet_invariants):
        baselines, output = dirs
        write_csv(output, "f.csv", ["Date", "a"], [["d1", "1"]])
        calls = quiet_invariants

        regen_or_compare(
            object(),
            baselines,
            output,
            regen=True,
            check_activation=lambda manager: calls.append("activation"),
        )

        assert calls == ["invariants", "activation"]
        assert (baselines / "f.csv").exists()

    def test_failing_guard_blocks_regen(self, dirs, quiet_invariants):
        baselines, output = dirs
        write_csv(baselines, "keep.csv", ["Date", "a"], [["d1", "1"]])
        write_csv(output, "f.csv", ["Date", "a"], [["d1", "1"]])

        def failing_activation(manager):
            raise AssertionError("mechanism did not fire")

        with pytest.raises(AssertionError, match="mechanism did not fire"):
            regen_or_compare(
                object(),
                baselines,
                output,
                regen=True,
                check_activation=failing_activation,
            )

        assert (baselines / "keep.csv").exists()
        assert not (baselines / "f.csv").exists()

    def test_compare_mode_runs_no_guards(self, dirs):
        # comparison never calls the guards (the dedicated tests own them) —
        # a guard failure must not be able to mask the golden diff
        baselines, output = dirs
        for directory in dirs:
            write_csv(directory, "f.csv", ["Date", "a"], [["d1", "1"]])

        regen_or_compare(
            object(),
            baselines,
            output,
            regen=False,
            check_activation=lambda manager: pytest.fail("guard called"),
        )
