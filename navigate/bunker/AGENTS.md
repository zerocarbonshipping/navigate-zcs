<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Bunker

Allocates fuel to vessels each time step with a linear program that mimics
competition between vessels under technical constraints (tanks, pilot fuel,
energy and mass balance), fuel supply (a fair share of what ports can deliver)
and regulation (remedial cost). It runs twice per step: the `EXPECTED` pass
yields the expectations and shadow prices that steer investment, speed and
conversion decisions elsewhere; the `EXISTING` pass settles what happened.
Within a pass the model is rebuilt and re-solved several times (fair-share
fixed point, threshold adjustment), so never assume a single solve.

- `constraints/` build and update rows on `alg: BunkerAlgorithm`, always the
  first argument; `transfer/` reads the solution back onto node expectations
  and profiles. Keep that symmetry.
- `solver.py` mimics the gurobipy API over HiGHS or Gurobi
  (`import navigate.bunker.solver as gp`); the shim keeps the foreign casing,
  which is why naming rules are relaxed for it.
- Variable and constraint creation order feeds solver determinism; enum
  iteration order is part of that order.
- Duals carry the sign convention of their constraint family (`<=` rows are
  negated to positive unit costs, equality rows are free-signed) and the
  per-vessel objective scaling. Binding is a tolerance question, and a dual is
  marginal only at the current basis, which can differ between machines. Read
  the builder of a constraint before using its dual.
- Consumption never exceeds supply by construction; unmet demand shows up as
  remedial units bought by the regulation, not as a supply gap.
