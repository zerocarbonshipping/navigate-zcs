<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Architecture

Navigate simulates the maritime transition as two sides that decide, shipowners
(`simulation/fleet/`) and fuel producers (`simulation/fuel/`), which interact
only through `core` expectations and the bunkering LP. `Simulation` in
`simulation/time_stepping.py` steps them through the dates of a deck, and
`driver/` runs it from the deck to the results file.

## Vocabulary

- General node: `ModelDefinition` or `BunkerOptions` (`core/general_nodes/`),
  one of each per run, with DEFINE attributes only.
- Calculator: a node evaluated through `.get` (`CALCULATOR_TYPES` in
  `core/node_type.py`); a `Scalar` (`core/scalar.py`) may stand in for one.
- Expectation: `node.expectation` (`core/expectations/`), a domain-owned node's
  state over the timeline, held as plain fields.
- Path: a quantity's value at every time step, the form most expectation
  fields take, alone or in a list or dict of paths. Writing it at `[idx:]`
  revises the outlook from a step on; writing it at `[idx]` records what one
  step realised.
- Results: `node.results` (`core/results/`) and the run-wide `GlobalResults`,
  what the results file reports: the fields declared with `result(unit)`.
- Node map: a node attribute derived from other nodes' attributes, such as
  `Vessel.usable_fuels`, written by `core/node_maps.py` only.
- Cohort: the assets of one age bin, held with their count in an `Increment`
  (`core/increment.py`), in service in `Fleet.increments` and
  `Producer.increments`, awaiting delivery in `Producer.pipeline`;
  `simulation/cohort.py` accounts for them.
- Count: the number of vessels or plants a value stands for, fractional as
  cohorts split and scrap in shares. A `Vessel` node is a vessel type and a
  `Plant` node a plant type; their expectations, and a vessel's results, hold
  the values of one vessel or plant. A total is such a value times a count: a
  port's bunker mass adds each vessel's bunkered mass times its count, and a
  fleet's results add its vessels' results weighted by their counts.
  `FleetExpectation.count` holds each vessel type's count per bunkering scope;
  in the expected scope a type allowed as a newbuild but with no vessels at a
  step carries a small count, so that it enters the LP.
- Time is measured in days or in years:
  - In days: `Simulation.timeline`, counted from the start date, and a step's
    size, from the date before (`Simulation._time_step_at`). The first step's
    size is taken as one year (`YEAR`).
  - In years: ages (`Increment`) and the `ResultsContext` timeline. The results
    file divides a `per_step` result by its step length in years
    (`step_lengths`), to a per-year rate.
- Bunkering LP (`simulation/bunker/`), run as two `BunkerAlgorithm`s: the
  existing scope solves the current step for the fleet as it stands, the
  expected scope every step to the horizon for the decisions.
- Domain: a package under `simulation/`; fleet and fuel are the two sides.

## A run

`main` in `app/cli.py` calls `run_deck` in `driver/run.py`, which the test
suites also call and which holds the sequence: parse, `Simulation.initialize`,
per date `Parser.read_events` then `Simulation.step`, `Simulation.finish`,
`write_results`. `parser/parser.py` and its phase modules describe the parser's
four phases. A declaration no chain of references connects to a root type is
pruned, never constructed.

`Simulation._perform_time_step` holds the exact order of a step: the first sets
up the existing fleet and production, evolution runs from the second on. The
expected scope runs before the decisions it informs and the existing scope
after them, each on inputs recalculated just before it, so the step's fuel goes
to the fleet those decisions left. The emission coefficients are computed once
for both scopes, as nothing they read changes later in a step.

## Package map

- `simulation/`: the model; `Simulation` orchestrates and does no model work.
  - `fleet/` owns `Fleet` and `Vessel`, `fuel/` owns `Producer`, `Plant` and
    `Port`, `policy/` owns `Regulation` and `Levy`. Each such
    `core/nodes/x.py` has `core/expectations/x_expectation.py` and
    `core/results/x_results.py`. The node's calculations live in its owning
    domain.
  - `bunker/` owns no node; its settings are the general node `BunkerOptions`.
    It reads the LP's regulation inputs from the expectations `policy/` writes.
  - `economics/` (valuation and choice) and `cohort.py` serve fleet and fuel.
- `core/`: the model definition only.
  - Node classes, which hold state and, for the calculators, value semantics.
    A file in `nodes/` holds one class, a node class or a base shared by node
    classes, and nothing else: no module-level helper or constant. Beyond a
    calculator's value semantics, node methods stay thin, delegating rather
    than computing. Logic or a table they need lives in a flat module of
    `core/`.
  - `expectations/` and `results/`.
  - Flat modules for the DSL values, the registries, the sweeps and the node
    maps.
- `parser/`, `output/`, `driver/`, `app/` (its `RunLog` alone configures
  logging), `util/` and `exceptions.py`, as their docstrings say.

Fleet, fuel and policy share a file layout:

- `initialization.py` (fleet and fuel only) sets up the first step's fleet or
  production.
- `expectation.py` holds expectations from the deck's inputs at the start of
  each step. In fleet and fuel it also holds the forecast of the fleet's or
  producer's own evolution.
- `results.py` records results at the end of each step.
- `post_process.py` derives results from the time steps' results after the
  run.

Every other module of these domains is named for a concept of the domain. It
writes the expectations it computes itself, deck-derived or not.

A package's public names are what its `__init__.py` re-exports, imported from
the package. A leading underscore means imported only inside the package.

`core/` and `util/` re-export only part, the rest imported by module path.

An `__init__.py` holding only a docstring is deliberate and gains no
re-exports, for one of two reasons:

- In `navigate/`, `simulation/`, `core/nodes/` and `core/general_nodes/`,
  re-exports would load far more than an import needs.
- In `simulation/bunker/_constraints/` and `simulation/bunker/_transfer/`, the
  bunker modules import each module of these packages by name.

## Layering

In the table:

- A unit is a package or module with a row.
- `__init__` stands for `navigate/__init__.py`, and `simulation` for
  `simulation/__init__.py` alone.
- `foundation` stands for `util/` and `exceptions.py`.
- `domains` stands for the five domains.

```
util, __init__, simulation         → (nothing)
exceptions                         → util
core                               → foundation
simulation.economics               → core, foundation
simulation.cohort                  → core, foundation
simulation.fleet, simulation.fuel  → simulation.economics, simulation.cohort,
                                     core, foundation
simulation.bunker,
simulation.policy                  → core, foundation
parser, output                     → core, foundation
app                                → driver, foundation
simulation.time_stepping           → domains, core, foundation
driver                             → simulation.time_stepping, domains,
                                     parser, output, core, foundation
__main__                           → app
```

A file belongs to the longest unit containing it. It imports only its own unit
and the units right of that unit's arrow, type-only imports included. Units
sharing a row do not import each other.

The table says what a unit may import, not where code belongs. Code goes in
the package of its topic, never in one chosen because every caller may import
it: `simulation/economics/` holds valuation and choice, not whatever fleet and
fuel share. Logic two domains share that has no home on its topic is a
structure to rework upstream, raised with the owners, not a reason to use a
package both may import.

A new top-level module or package needs a row, as does a new module or package
directly under `simulation/`.

No row may let either side of these pairs import the other:

- Any two of bunker, fleet, fuel and policy.
- Economics or cohort, and bunker or policy.
- `parser` and `output`.
- `parser` or `output`, and a simulation unit.

Inside `core/`, runtime imports run one way:

- `nodes/` imports `expectations/`, `results/` and the flat modules directly
  in `core/`.
- `expectations/`, `results/` and `general_nodes/` import only the flat
  modules.
- The flat modules import no subpackage. One that needs a node class imports
  it under `TYPE_CHECKING`. The exception is `core/node_registry.py`, whose
  registries read the classes of `nodes/` and `general_nodes/` at runtime, by
  design.

Imports are absolute (ruff `TID252`).

Nothing checks the layering mechanically; review holds it. A task that needs
the layering changed changes the table with the code.

## Data-flow invariants

- A value computed during the time loop that one of fleet, fuel, policy and
  bunker reads from another lives on the node's `expectation`: the computing
  domain writes the field, the others only read it. The one other route is
  `Simulation` handing a value on as a call argument, such as the counts a
  bunkering LP ran with to the policy functions settling it.
- The plain node attributes another domain reads are:
  - DSL inputs;
  - what the lifecycle hooks derive from them (`Route.distinct_ports`);
  - node maps;
  - `Vessel.primary_fuel_type` and `Vessel.fleet_assignment`, which the first
    step's fleet initialization sets once and the bunkering LP reads.

  The rest of a node's `# internal variables` group, such as
  `Fleet.increments`, is state its owning domain keeps for itself.
- A node map that derives from DEFINE-only attributes is written once, by
  `Simulation.initialize`. A node map that derives from what events can change
  is written every time step.
- An expectation field holds what its writer stored, or the default its
  constructor gave it, as `core` holds no model work. A quantity derived from
  stored values is computed in the domain that reads it. Where the parts of a
  sum are never read on their own, the writer stores the sum.
- `results` is output for the results file, never a decision's input. A step
  writes a result where it computes it. A result computed from other results is
  written after the run, once those are final, by the domain's `post_process`
  module or, for the global sums, `Simulation.finish`.
- `simulation/` handles no files, console output or arguments. Its one file
  output is an infeasible bunkering LP, written to the path `Simulation` is
  given, with its IIS beside it where the solver finds one.

## Node lifecycle

`Builder` (`parser/_build.py`) runs steps 1 to 8 as the DEFINE pass, and step 9
follows that pass once, before the first date. At every date, events or none,
steps 2 to 8 run again, then step 10.

1. `__init__(name)`: once per kept declaration, in the DEFINE pass only.
2. The DSL setters:
   - in the DEFINE pass, the last assignment of each attribute;
   - at each date, every assignment of the date's events.
3. The parser raises where a `required=True` setter never ran for the node.
4. `initialize_dependencies(...)`, from `seed_dependencies` in
   `core/lifecycle.py`, the one method handed the registries.
5. The DSL commands: one call per command.
6. `build_table` on every table calculator, which builds a table set since
   the last pass.
7. The sweep that applies defaults:
   - in the DEFINE pass, the `initialize` sweep: `apply_defaults`, then
     `apply_command_defaults`;
   - at each date, the `reinitialize` sweep: `apply_command_defaults` only.
8. The `validate` sweep: `check_requirements`, then `check_consistency`.
9. `Simulation.initialize`, once: `initialize_expectation`,
   `initialize_results`.
10. `Simulation` calls `check_dynamic_consistency` at the start of each step,
    never in the DEFINE pass.

`Node` (`core/node.py`) declares five hooks: `apply_defaults`,
`apply_command_defaults`, `check_requirements`, `check_consistency` and
`check_dynamic_consistency`. A node overrides these, never the `@final`
`initialize` and `reinitialize`. The three `initialize_*` methods are not
declared on `Node`. `seed_dependencies` and `Simulation` call them type by
type.

`None` on a DSL input means unassigned; no DSL value is `None`. General nodes
take their assignments and the required-attribute check only.
