# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Bake the results the leadership demo shows without solving them on stage.

Runs the three reference scenarios on the coarse grid and the Horizon study
demo.hor, in a scratch copy of notebook 2's global case with overlay/ on top,
and writes what the notebook loads into results/:

    results/parquets/<scenario>.parquet   the reference scenarios
    results/study/demo.parquet            the study, as Lantern reads it
    results/study/study.json              every run with its sampled values
    results/study/demo_archive.parquet    every run, only the series the demo reads

Run it with the Python of an environment that has Navigate, Horizon and Lantern:

    .venv/bin/python demo/leadership/bake.py /tmp/demo-bake
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
CASE = REPOSITORY / "docs" / "notebooks" / "notebook_2" / "global_case"
SCENARIOS = (
    "basecase_no_regulation",
    "basecase_mid_regulation",
    "basecase_strong_regulation",
)

# the series the demo reads from every run of the study: emissions and fuel mix
# of the world fleet, and what the fleets paid against the work they did
ARCHIVE_SERIES = (
    (pl.col("kind") == "global")
    & pl.col("attribute").is_in(["total_equivalent_wtw", "consumed_energy"])
) | (
    (pl.col("kind") == "fleet") & pl.col("attribute").is_in(["expenses", "cargo_miles"])
)


def bake(work: Path) -> None:
    """Solve the scenarios and the study in work and write what the demo loads to results/."""
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(CASE, work)
    shutil.copytree(HERE / "overlay", work, dirs_exist_ok=True)

    # Horizon starts the navigate on PATH, so this environment's comes first
    tools = Path(sys.executable).parent
    env = os.environ | {
        "ASSUMPTIONS_DATA_DIR": str(REPOSITORY / "assumptions"),
        "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
    }

    references = [
        subprocess.Popen(
            ["navigate", f"{scenario}.nav", "--set", "GRID=coarse"],
            cwd=work,
            env=env,
            stdout=subprocess.DEVNULL,
        )
        for scenario in SCENARIOS
    ]
    if any(run.wait() for run in references):
        sys.exit("a reference scenario failed: see its log in parquets/../logs")

    subprocess.run(["horizon", "run", "demo.hor"], cwd=work, env=env, check=True)
    subprocess.run(["horizon", "collect", "demo.hor"], cwd=work, env=env, check=True)

    results = HERE / "results"
    shutil.rmtree(results, ignore_errors=True)
    (results / "parquets").mkdir(parents=True)
    (results / "study").mkdir()
    for scenario in SCENARIOS:
        shutil.copy(work / "parquets" / f"{scenario}.parquet", results / "parquets")
    shutil.copy(work / "study" / "demo.parquet", results / "study")
    pl.read_parquet(work / "study" / "demo_archive.parquet").filter(
        ARCHIVE_SERIES
    ).write_parquet(results / "study" / "demo_archive.parquet")

    # the study names the files it ran by their path on this machine;
    # the demo needs only the runs
    study = json.loads((work / "study" / "study.json").read_text(encoding="utf-8"))
    study["hor"] = "demo.hor"
    study["unc"] = "basecase_mid_regulation.unc"
    study["navigate"] = "navigate"
    (results / "study" / "study.json").write_text(
        json.dumps(study, indent=1), encoding="utf-8"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    bake(Path(sys.argv[1]).resolve())
