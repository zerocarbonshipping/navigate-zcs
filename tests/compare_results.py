# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Compare the results of a fixed set of decks between two installs of Navigate.

A change meant to leave simulation results alone (a pull request labelled
`maintenance`) must leave every result of these decks where it was, up
to rounding. `snapshot` runs the decks with the Navigate that the running
interpreter imports, and writes one snapshot per deck (helpers/snapshot.py);
`diff` compares two such directories and fails on any difference beyond
rounding. CI runs `snapshot` once with the pull request merged into its base
and once with that base, each from its own copy of this script and its decks,
so a change that migrates the decks to new DSL still compares. Each deck is
copied into a temporary directory before it runs, so the checkout receives no
output, and each run uses HiGHS, so that a Gurobi licence on one side cannot
move the results.

    python tests/compare_results.py snapshot --assumptions ./assumptions --out base/
    python tests/compare_results.py diff base/ head/
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

# run as a script, so its own directory, tests/, is first on sys.path
from helpers import snapshot as snapshots
from helpers.combinations import COMBINATIONS, write_combination

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]

SOLVER = "highs"

# output a local run may have left beside a committed deck
_RUN_OUTPUT = shutil.ignore_patterns("plots*", "output", "*.xlsx", "*.log", "*.pkl")


def _copy(source: Path) -> Callable[[Path], None]:
    """Return a writer that copies the committed deck directory `source`."""

    def write(deck_dir: Path) -> None:
        shutil.copytree(source, deck_dir, dirs_exist_ok=True, ignore=_RUN_OUTPUT)
        nav = deck_dir / f"{source.name}.nav"
        nav.rename(deck_dir / f"{deck_dir.name}.nav")

    return write


def _combination(*layers: tuple[str, dict[str, object]]) -> Callable[[Path], None]:
    """Return a writer for the combination base deck plus the given layers."""
    return lambda deck_dir: write_combination(deck_dir, COMBINATIONS, *layers)


# Every deck the comparison runs, by the name of its snapshot. The combination
# decks reach the bunker, levy, conversion and technology paths on pinned
# inputs; the attribute coverage deck sets every attribute and command once;
# the examples run the installation's default assumptions at scale.
DECKS: dict[str, Callable[[Path], None]] = {
    "combination_base": _combination(),
    "combination_mechanisms": _combination(
        ("levy.inc", {"scheme": "BOTH", "scope": "WTW", "lower_threshold": 85.0}),
        ("fuel_conversion.inc", {}),
        ("technology_uptake.inc", {"capex": 1e6}),
    ),
    "attribute_coverage": _copy(
        REPO_ROOT / "tests" / "end_to_end" / "simulations" / "attribute_coverage"
    ),
    **{
        f"example_{n}": _copy(REPO_ROOT / "simulations" / "examples" / f"example_{n}")
        for n in (1, 2, 3)
    },
}


def snapshot_decks(assumptions: Path, out: Path, names: list[str]) -> None:
    """Run each named deck and write its snapshot to `<out>/<name>.npz`."""
    # imported here so `diff` runs without Navigate installed
    from navigate.driver import run_deck

    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            deck_dir = Path(tmp) / name
            deck_dir.mkdir()
            DECKS[name](deck_dir)
            results = run_deck(
                deck_dir / f"{name}.nav",
                data_dir=assumptions,
                solver=SOLVER,
            )
            snap = snapshots.snapshot(results)
            snapshots.save(out / f"{name}.npz", snap)
            print(f"{name}: {len(snap)} arrays")


def _summary(lines_by_deck: dict[str, list[str]]) -> str:
    """Render the differences as Markdown for the CI job summary."""
    if not any(lines_by_deck.values()):
        return "## Compare results\n\nNo deck's results moved.\n"
    text = "## Compare results\n\n| Deck | Differences |\n|---|---|\n"
    text += "".join(
        f"| {deck} | {len(lines)} |\n" for deck, lines in lines_by_deck.items()
    )
    for deck, lines in lines_by_deck.items():
        if lines:
            body = "\n".join(lines)
            text += (
                f"\n<details><summary>{deck}</summary>\n\n"
                f"```\n{body}\n```\n\n</details>\n"
            )
    return text


def diff_dirs(base: Path, head: Path, rtol: float, atol: float) -> bool:
    """Print the differences between two snapshot directories; True if none."""
    names = sorted(
        {p.stem for p in base.glob("*.npz")} | {p.stem for p in head.glob("*.npz")}
    )
    lines_by_deck: dict[str, list[str]] = {}
    for name in names:
        base_file, head_file = base / f"{name}.npz", head / f"{name}.npz"
        if not base_file.exists() or not head_file.exists():
            side = "base" if not base_file.exists() else "head"
            lines_by_deck[name] = [f"no snapshot on the {side} side"]
            continue
        lines_by_deck[name] = snapshots.diff(
            snapshots.load(base_file), snapshots.load(head_file), rtol, atol
        )

    for name, lines in lines_by_deck.items():
        print(f"{name}: {'unchanged' if not lines else f'{len(lines)} differences'}")
        for line in lines:
            print(f"  {line}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as f:
            f.write(_summary(lines_by_deck))
    return not any(lines_by_deck.values())


def main() -> int:
    """Run the subcommand the command line names; return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    commands = parser.add_subparsers(dest="command", required=True)

    snap = commands.add_parser("snapshot", help="run the decks and snapshot them")
    snap.add_argument("--assumptions", type=Path, default=REPO_ROOT / "assumptions")
    snap.add_argument("--out", type=Path, required=True)
    snap.add_argument("--deck", action="append", choices=DECKS, dest="decks")

    compare = commands.add_parser("diff", help="compare two snapshot directories")
    compare.add_argument("base", type=Path)
    compare.add_argument("head", type=Path)
    compare.add_argument("--rtol", type=float, default=snapshots.ROUNDING_RTOL)
    compare.add_argument("--atol", type=float, default=snapshots.ROUNDING_ATOL)

    args = parser.parse_args()
    if args.command == "snapshot":
        snapshot_decks(args.assumptions.resolve(), args.out, args.decks or list(DECKS))
        return 0
    return 0 if diff_dirs(args.base, args.head, args.rtol, args.atol) else 1


if __name__ == "__main__":
    sys.exit(main())
