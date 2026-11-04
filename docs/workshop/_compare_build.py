# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Compare the decks of a prompt test build with their reference decks, by their headline numbers.

Run from the repository root, one BUILD=REFERENCE pair per deck:

    python docs/workshop/_compare_build.py BUILD.nav=REFERENCE.nav [BUILD.nav=REFERENCE.nav ...]

For example, a cold build of the Rhine prompt against example_6:

    python docs/workshop/_compare_build.py \\
        .claude/worktrees/<agent>/simulations/user/rhine_inland/rhine.nav=simulations/examples/example_6/example_6.nav

The reference of a prompt is the repository deck built from it (docs/workshop/AGENTS.md, "Testing the
prompts"). Each pair is solved and printed side by side: well-to-wake emissions in the first and last year
and summed, the non-fossil share and the energy by fuel in the last year, and the freight rate. A number
that differs by more than TOLERANCE is flagged, and the script exits 1 if any is.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("docs/workshop").resolve()))
from _results import run_case, summarise  # noqa: E402
from _solver import guard_interior_point  # noqa: E402

TOLERANCE = 0.01      # relative, 1 %
SHARE_TOLERANCE = 1.0  # percentage points, for shares


def headline(s):
    years = s["years"]
    total = sum(float(v[-1]) for v in s["by_year"].values()) or 1.0
    rows = {f"well-to-wake {years[0]}, kt": float(s["wtw"][0]),
            f"well-to-wake {years[-1]}, kt": float(s["wtw"][-1]),
            "well-to-wake summed, kt": float(s["wtw"].sum()),
            f"freight rate {years[-1]}, USD/k cargo-mile": float(s["freight"][-1]),
            f"non-fossil {years[-1]}, %": float(s["alt_last"])}
    for fuel, v in s["by_year"].items():
        rows[f"{fuel} {years[-1]}, % of energy"] = 100.0 * float(v[-1]) / total
    return rows


def main(pairs):
    guard_interior_point()
    flagged = 0
    for pair in pairs:
        build, _, reference = pair.partition("=")
        assert reference, f"expected BUILD.nav=REFERENCE.nav, got {pair!r}"
        b, r = headline(summarise(run_case(build))), headline(summarise(run_case(reference)))
        print(f"\n{Path(build).name}  vs  {Path(reference).name}")
        for key in sorted(set(b) | set(r), key=lambda k: (k not in r, k)):
            vb, vr = b.get(key, 0.0), r.get(key, 0.0)
            if "%" in key.split(",")[-1]:
                off = abs(vb - vr) > SHARE_TOLERANCE
            else:
                off = abs(vb - vr) > TOLERANCE * max(abs(vr), 1e-9)
            flagged += off
            print(f"  {key:44} {vb:12,.2f} {vr:12,.2f}  {'<-- differs' if off else ''}")
    print(f"\n{flagged} number(s) outside tolerance" if flagged else "\nall within tolerance")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
