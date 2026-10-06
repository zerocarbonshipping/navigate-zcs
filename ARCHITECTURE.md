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
  DSL keyword), maps between nodes derived from static node attributes
  (`node_maps.py`), the records nodes hold (`increment.py`
  asset cohorts, `technology_package.py`), singleton general nodes, `expectations/`
  (cross-module dynamic state), `profiles/` (end-of-run output containers) and
  the `SimulationResults` record a finished run hands to output
  (`simulation_results.py`).
- `parser/` — reads `.nav`/`.inc` decks into nodes (Lark grammar).
- `fleet/` — the shipowner domain: voyage physics and energy demand,
  valuation (charter rates, technology package calculations, marginal-saving
  heuristics) and the speed, technology, fuel-conversion and newbuild/scrap
  decisions.
- `fuel/` — the fuel-supply domain: production and delivery economics,
  supply/demand balancing, port fuel supply, and producer capacity planning.
- `economics/` — asset-agnostic valuation-and-choice toolkit (cash flows,
  NPV/levelized cost, discrete choice) used by both domains.
- `bunker/` — the per-time-step bunkering LP: build → solve → transfer.
- `policy/` — regulation/levy emission coefficients, jurisdiction
  attribution, and regulation flexibility-cost beliefs.
- `output/` — turns a run's `SimulationResults` into Excel/CSV reports and
  figures; `output/plots/` renders the latter.
- `util/` — dependency-free helpers: collections, dates, naming, numerics,
  internal types and unit conversion factors; imports nothing from
  `navigate` outside `util/`.
- `logging_.py` — run logging; `exceptions.py` — the `NavigateError`
  hierarchy; `__main__.py` — the CLI.

## Layering

```
util        → (nothing)
core        → util
economics   → core, util
policy      → core, util
fleet, fuel → core, economics, util
bunker      → core, policy, util
output      → core, util
simulation  → everything
```

`exceptions.py` and `logging_.py` are foundation modules that import only
`util`. `exceptions.py` is available to every layer alongside `util`;
`logging_.py` to every layer above `core`.
`tests/unit/test_layering.py` enforces that `core/` imports nothing from
`navigate` beyond `core/`, `util/` and `exceptions.py`, type-only imports
included, that `output/` imports nothing beyond `output/`, `core/`, `util/`
and the foundation modules, and that `exceptions.py` and `logging_.py`
import only `util`.

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

## Node lifecycle

The parser brings a node to a usable state through two `@final` entry points
on `Node`; a node overrides the hooks they call, never the entry points.

- `initialize()` runs once, after the DEFINE block: `check_requirements()`,
  `apply_defaults()`, then `reinitialize()`.
- `reinitialize()` runs after DEFINE and again after every event read:
  `apply_command_defaults()`, then `check_consistency()`.

Before `initialize()`, the parser checks the required attributes. The attribute
registry in `navigate/parser/_attributes.py` lists, per node type, the
attributes a deck must assign; the parser records every setter it runs, and
once the DEFINE block is read it raises `UnassignedAttributeError` for a
required attribute no setter reached. The check runs after the
unreachable-node prune, so a pruned node is never checked, and before
`initialize_dependencies(...)`, the commands and the hooks, so no node reads
another's required attribute unset. The general nodes are checked before
anything reads the start date. A node declares a required attribute without
a value, so it is absent from the node's `__dict__` until its setter runs.

What each hook holds:

- `check_requirements()` raises where an attribute the node cannot run
  without is unassigned and the registry cannot say so: a list left empty,
  or an attribute required only under a condition on others. `None` on a
  node attribute always means unassigned: the grammar has no `none`
  literal, and every `assign_*` in `navigate/core/assign.py` returns a value
  or raises, so no DSL value is ever `None`.
- `apply_defaults()` fills a value derived from the size or the value of
  another attribute.
- `apply_command_defaults()` fills the entries of the command-written
  dictionaries that `initialize_dependencies(...)` cannot seed with their
  default, such as the keys a command creates, and resolves the
  dictionaries into the form the node reads.
- `check_consistency()` raises where attributes contradict each other and
  warns where one is unused.
- `check_dynamic_consistency(times, dates)` raises where time-varying
  attributes contradict each other anywhere over the remaining timeline. Not
  part of `initialize()`/`reinitialize()`: `SimulationManager` calls it once
  per time step, before the expectations, over `timeline[idx:]` and
  `dateline[idx:]`, because a Forecast's value over the future is only known
  against the timeline, which `check_consistency()` does not see.

The cadences differ because no deck can unassign a required attribute or
create a node after DEFINE, while a `SECTION_BOTH` attribute may be
re-assigned between time steps and a command may create a dictionary key
mid-run.

General nodes accept attributes in `SECTION_DEFINE` only, so `_GeneralNode`
has no lifecycle hooks: the required-attribute check is all they need.

Anything derived from the node registries stays in
`initialize_dependencies(...)`, the only hook the parser hands them. It
also seeds every registry-keyed entry of a command-written dictionary with
its default, or with `None` where unassigned means something to the reader,
before the commands run.

## Naming conventions

- `fleet/` and `fuel/` mirror each other deliberately (`initialization.py`,
  `evolution.py`, `planning.py`, `aggregation.py`): same name, same role in
  each domain.
- A leading underscore on a module or class means package-private; anything
  used across package boundaries carries a public name.
- Each package's `__init__.py` re-exports its externally consumed entry
  points — read it first to learn the package's API.
