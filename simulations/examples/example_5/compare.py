# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
"""Run example_5's three decks and compare the regional and international fleets.

Run from the repository root:  python simulations/examples/example_5/compare.py
"""
import argparse
import contextlib
import io
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path("docs/workshop").resolve()))
from _solver import guard_interior_point  # noqa: E402

from navigate.manager import SimulationManager  # noqa: E402

guard_interior_point()

HERE = Path("simulations/examples/example_5")
DECKS = ["no_policy", "current_rules", "extended"]
ARGS = argparse.Namespace(data_dir=Path("./assumptions"), solver=None)
SHOW = [2030, 2040, 2050]
GROUPS = {"regional": "reg_", "international": "intl_"}


def run(name):
    m = SimulationManager()
    with contextlib.redirect_stdout(io.StringIO()):
        m.read_deck(HERE / f"example_5_{name}.nav", ARGS)
        m.run()
    return m


def summarise(m):
    years = m.get_dateline().astype("datetime64[Y]").astype(int) + 1970
    out = {"years": years, "groups": {}, "coverage": {}, "production": {}}
    for group, prefix in GROUPS.items():
        fleets = [f for n, f in m.nodes.fleets.items() if n.startswith(prefix)]
        g = {"ships": 0, "wtw": 0, "fuel_cost": 0, "reg_cost": 0, "energy": {}, "fuel_mass": 0}
        for f in fleets:
            p = f.profile
            g["ships"] = g["ships"] + sum(np.nan_to_num(v) for v in p.get_existing_vessels().values())
            g["wtw"] = g["wtw"] + np.nan_to_num(p.get_total_equivalent_WTW())
            g["fuel_cost"] = g["fuel_cost"] + np.nan_to_num(p.get_total_fuel_expenses())
            g["reg_cost"] = g["reg_cost"] + np.nan_to_num(p.get_regulation_expenses())
            g["fuel_mass"] = g["fuel_mass"] + np.nan_to_num(p.get_total_consumed_mass())
            for fuel, e in p.get_fuel_type_energy().items():
                g["energy"][str(fuel)] = g["energy"].get(str(fuel), 0) + np.nan_to_num(e)
        out["groups"][group] = g
    for name, reg in m.nodes.regulations.items():
        out["coverage"][name] = sorted({v.split("_")[0] + "_" + v.split("_")[1]
                                        for v, inc in reg.include_vessel.items() if inc})
    for name, prod in m.nodes.producers.items():
        out["production"][name] = {str(k): np.nan_to_num(v) for k, v in prod.profile.get_production_energy().items()}
    return out


def table(results):
    for group in GROUPS:
        print(f"\n=== {group} fleet ===")
        for name, r in results.items():
            y = list(r["years"])
            g = r["groups"][group]
            print(f"  {name}:")
            for yr in SHOW:
                i = y.index(yr)
                total = sum(e[i] for e in g["energy"].values()) or 1
                mix = ", ".join(f"{k} {100 * e[i] / total:.0f}%" for k, e in
                                sorted(g["energy"].items(), key=lambda kv: -kv[1][i]) if e[i] / total > 0.005)
                print(f"    {yr}: {g['ships'][i]:5.0f} ships, fuel {g['fuel_mass'][i] / 1e3:6.0f} kt, "
                      f"WTW {g['wtw'][i] / 1e6:5.2f} Mt, fuel {g['fuel_cost'][i] / 1e6:6.0f} M$, "
                      f"policy {g['reg_cost'][i] / 1e6:5.0f} M$ | {mix}")
            cum = g["wtw"].sum() / 1e6
            print(f"    cumulative WTW 2026-2050: {cum:.1f} Mt; fuel+policy cost {(g['fuel_cost'].sum() + g['reg_cost'].sum()) / 1e9:.2f} bn$")
    print("\n=== coverage ===")
    for name, r in results.items():
        print(f"  {name}: {r['coverage']}")
    print("\n=== new-fuel production, PJ in 2030 / 2040 / 2050 ===")
    for name, r in results.items():
        y = list(r["years"])
        for prod, fuels in r["production"].items():
            for fuel, e in fuels.items():
                if e.sum() > 0:
                    print(f"  {name} {prod} {fuel}: " + " / ".join(f"{e[y.index(yr)] / 1e6:.2f}" for yr in SHOW))


if __name__ == "__main__":
    names = sys.argv[1:] or DECKS
    results = {n: summarise(run(n)) for n in names}
    with open(HERE / "compare.pkl", "wb") as fh:
        pickle.dump(results, fh)
    table(results)
