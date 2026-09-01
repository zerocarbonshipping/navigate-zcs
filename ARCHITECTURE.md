<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Architecture

Navigate simulates the maritime transition as two decision-making domains —
shipowners (`fleet/`) and fuel producers (`fuel/`) — built on shared
foundations and coordinated by a per-time-step loop in `simulation.py`. The
domains never import each other: they interact only through `core`
expectations and the bunkering LP. This file maps the code; the DSL and model
behavior are documented in `docs/reference_manual/`.

## Package map

- `simulation.py` — the simulation loop (`SimulationManager`); pure
  orchestration: each phase calls a domain entry point.
- `core/` — the model definition: DSL value infrastructure (assignment
  validation, expressions, tables), the node classes (`core/nodes/`, one per
  DSL keyword), singleton general nodes, `expectations/` (cross-module
  dynamic state) and `profiles/` (end-of-run output containers).
- `parser/` — reads `.nav`/`.inc` decks into nodes (Lark grammar).
- `fleet/` — the shipowner domain: voyage physics and energy demand,
  valuation (charter rates, technology packages, marginal-saving heuristics)
  and the speed, technology, fuel-conversion and newbuild/scrap decisions.
- `fuel/` — the fuel-supply domain: production and delivery economics,
  supply/demand balancing, port fuel supply, and producer capacity planning.
- `economics/` — asset-agnostic valuation-and-choice toolkit (cash flows,
  NPV/levelized cost, discrete choice) used by both domains.
- `bunker/` — the per-time-step bunkering LP: build → solve → transfer.
- `policy/` — regulation/levy emission coefficients, jurisdiction
  attribution, and regulation flexibility-cost beliefs.
- `output/` — turns a run into artifacts: Excel/CSV reports and plot data;
  `output/plots/` renders the figures.
- `util/` — dependency-free helpers; imports nothing from `navigate`.
- `logging_.py` — run logging; `exceptions.py` — the `NavigateError`
  hierarchy; `__main__.py` — the CLI.

## Layering

```
util        → (nothing)
core        → util
economics   → core, util
policy      → core, util
fleet, fuel → core, economics, util
bunker      → core, policy, util (+ fleet.fuel_option)
output      → core, util
simulation  → everything
```

Known back-edges: `core/nodes/fleet.py` and `core/nodes/producer.py`
delegate behavior into `fleet/`/`fuel/`
([#22](https://github.com/zerocarbonshipping/navigate-zcs/issues/22)), and
core table/report/plot nodes call into `logging_`/`output`.

## Data-flow invariants

- Dynamic results that cross modules flow through the node's `expectation`:
  the computing module writes via `set_*`/`add_*`, everyone else reads via
  `get_*`.
- `profile` is output storage for end-of-simulation reports and plots; it is
  never read as an input to a simulation decision. Inside the
  profile-aggregation phase (`SimulationManager._calculate_profile`) and
  post-processing, deriving one profile value from an already-written one is
  fine — nothing downstream of those phases feeds a decision.
- Direct attribute access (`node.some_input.get()`) is reserved for
  DSL-defined inputs.

## Naming conventions

- `fleet/` and `fuel/` mirror each other deliberately (`evolution.py`,
  `aggregation.py`, `utils.py`): same name, same role in each domain.
- A leading underscore on a module or class means package-private; anything
  used across package boundaries carries a public name.
- Each package's `__init__.py` re-exports its externally consumed entry
  points — read it first to learn the package's API.
