# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
One deck gives identical results every time it runs.

The deck is compare_results.py's combination base with a levy, fuel conversion
and technology uptake on, so the bunker, policy and every fleet decision act.
Two runs in one process catch state that leaks from one run into the next; two
processes with different hash seeds catch results that depend on the iteration
order of a set or dict of strings. Every profile getter is compared, exactly:
on one machine and one solver nothing may move.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from compare_results import DECKS
from helpers import snapshot
from helpers.simulation import default_assumptions_dir, run_simulation

COMPARE_SCRIPT = Path(__file__).resolve().parents[1] / "compare_results.py"
DECK = "combination_mechanisms"

HASH_SEEDS = ("0", "1")

pytestmark = pytest.mark.slow


def test_two_runs_in_one_process_agree(tmp_path):
    snaps = []
    for name in ("first", "second"):
        deck_dir = tmp_path / name
        deck_dir.mkdir()
        DECKS[DECK](deck_dir)
        snaps.append(snapshot.snapshot(run_simulation(deck_dir)))

    assert snapshot.diff(*snaps) == []


def test_runs_under_different_hash_seeds_agree(tmp_path):
    snaps = []
    for seed in HASH_SEEDS:
        out = tmp_path / f"seed_{seed}"
        subprocess.run(
            [
                sys.executable,
                str(COMPARE_SCRIPT),
                "snapshot",
                "--assumptions",
                str(default_assumptions_dir()),
                "--out",
                str(out),
                "--deck",
                DECK,
            ],
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
            capture_output=True,
        )
        snaps.append(snapshot.load(out / f"{DECK}.npz"))

    assert snapshot.diff(*snaps) == []
