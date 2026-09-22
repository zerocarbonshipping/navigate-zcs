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
- `parser/` — reads `.nav`/`.inc` decks into nodes (Lark grammar) and drives
  the timeline.
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

## Core abstractions

- A **node** (`core/node.py`) is a deck entity: a name, a type string that is
  also the DSL keyword, and the `set_*` methods the deck may call. All nodes
  live in one registry (`core/node_registry.py`) that the simulation and the
  bunkering LP both hold.
- Each node owns an **expectation** and a **profile**. The expectation
  (`core/expectations/`) is forward-looking scratch state within one time
  step, indexed from now over a planning horizon and recomputed each step.
  The profile (`core/profiles/`) is the append-only record over the whole
  timeline that reports and plots read.
- An **increment** (`core/increment.py`) is a cohort of assets — vessels or
  plants — that entered service together; fleets and producers age and
  retire their stock as lists of increments.
- The **time loop** is driven by the parser: the deck's `EVENTS` are replayed
  date by date, and `SimulationManager._perform_time_step` sequences the
  domain calls for each date. The bunkering LP runs twice per step: the
  `EXPECTED` pass produces the expectations and shadow prices that
  investment, speed and conversion decisions react to; the `EXISTING` pass
  settles the step.
- Modules exchange results by **mutating nodes in place**: a domain function
  takes node dictionaries and a time index and writes expectations or
  profiles. There is no return-value plumbing between packages.

## Layering

```
util        → (nothing)
core        → util
economics   → core, util
policy      → core, util
fleet, fuel → core, economics, util
bunker      → core, policy, util (+ fleet.fuel_option)
output      → core, util (+ fleet.fuel_option)
simulation  → everything
```

`exceptions.py` and `logging_.py` are foundation modules available to every
layer alongside `util`.

Known back-edge: the core table nodes call into `logging_`, which itself
imports `core.unit`
([#22](https://github.com/zerocarbonshipping/navigate-zcs/issues/22)).
`tests/unit/test_layering.py` enforces that `core/` imports nothing from
`navigate` at runtime beyond `core/`, `util/`, `exceptions.py`, and
`logging_.py`; the sibling rule for the domain packages is not yet enforced
([#185](https://github.com/zerocarbonshipping/navigate-zcs/issues/185)).

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

## DSL surface

The grammar (`parser/grammar.lark`) is generic; what a deck may say about a
node is defined in four places that move together:

- the node's `set_*` method in `core/nodes/`, whose docstring documents the
  attribute for users;
- the allow-list tables in `parser/` (`_attributes.py`, `_commands.py`);
- the node's page in `docs/reference_manual/`, hand-written with one heading
  per attribute and command;
- the editor highlighting bundles in `syntax/`.

`tests/attribute/` checks that the first two agree by running a deck that
exercises every registered name; nothing checks the manual page
([#184](https://github.com/zerocarbonshipping/navigate-zcs/issues/184)).

## Naming conventions

- `fleet/` and `fuel/` mirror each other deliberately (`initialization.py`,
  `evolution.py`, `planning.py`, `aggregation.py`, `utils.py`): same name,
  same role in each domain.
- A leading underscore on a module or class means package-private; anything
  used across package boundaries carries a public name.
- A package's `__init__.py` re-exports its externally consumed entry points —
  read it first to learn the package's API. `core/nodes/` and
  `core/general_nodes/` are the exception: their `__init__.py` is empty so
  that importing one node class does not load them all.
