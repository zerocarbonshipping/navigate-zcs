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
  state over the timeline, behind `set_*`, `add_*` and `get_*` accessors.
- Results: `node.results` (`core/results/`) and the run-wide `GlobalResults`,
  what the results file reports: the fields declared with `result(unit)`.
- Node map: a node attribute derived from other nodes' attributes, such as
  `Vessel.usable_fuels`, written by `core/node_maps.py` only.
- Cohort: the assets of one age bin, an `Increment` (`core/increment.py`), in
  service in `Fleet.increments` and `Producer.increments`, awaiting delivery in
  `Producer.pipeline`; `simulation/cohort.py` accounts for them.
- Time: `Simulation.timeline` holds days since the start date, and a step's
  size, from the date before (`Simulation._time_step_at`), is in days, the
  first taken as one year (`YEAR`). Ages are in years (`Increment`), as is the
  `ResultsContext` timeline; the results file divides a `per_step` result by
  its step length in years (`step_lengths`), to a per-year rate.
- Bunkering LP (`simulation/bunker/`), run as two `BunkerAlgorithm`s: the
  existing scope solves the current step for the fleet as it stands, the
  expected scope every step to the horizon for the decisions.
- Domain: a package under `simulation/`; fleet and fuel are the two sides.

## A run

`main` in `app/cli.py` calls `run_deck` in `driver/run.py`, which the test
suites also call and which holds the sequence: parse, `Simulation.initialize`,
per date `Parser.read_events` then `Simulation.step`, `Simulation.finish`,
`write_results`. `parser/parser.py` and its phase modules describe the parser's
four phases; a declaration no chain of references connects to a root type is
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
    `core/results/x_results.py`; its calculations live in its owning domain.
  - `bunker/` owns no node; its settings are the general node `BunkerOptions`.
    It reads the LP's regulation inputs from the expectations `policy/` writes.
  - `economics/` (valuation and choice) and `cohort.py` serve fleet and fuel.
- `core/`: the model definition only: node classes, which hold state and, for
  the calculators, value semantics; `expectations/`; `results/`; flat modules
  for the DSL values, the registries, the sweeps and the node maps.
- `parser/`, `output/`, `driver/`, `app/` (its `RunLog` alone configures
  logging), `util/` and `exceptions.py`, as their docstrings say.

Fleet, fuel and policy share a file layout: `initialization.py` (fleet and fuel
only) sets up the first step's fleet or production, `expectation.py` holds
expectations from the deck's inputs at the start of each step and, in fleet and
fuel, the forecast of the fleet's or producer's own evolution, `results.py`
records results at the end of each step, and `post_process.py` derives results
from those after the run; every other module is named for a concept of the
domain and writes the expectations it computes itself, deck-derived or not.

A package's public names are what its `__init__.py` re-exports, imported from
the package; a leading underscore means imported only inside the package.
`core/` and `util/` re-export only part, the rest imported by module path. An
`__init__.py` holding only a docstring is deliberate and gains no re-exports:
in `navigate/`, `simulation/`, `core/nodes/` and `core/general_nodes/` one
would load far more than an import needs, and the bunker modules import those
of `_constraints/` and `_transfer/` by name.

## Layering

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

A unit is a package or module with a row; `__init__` is `navigate/__init__.py`
and `simulation` is `simulation/__init__.py` alone. The foundation is `util/`
and `exceptions.py`, `domains` the five domains. A file belongs to the longest
unit containing it and imports only its unit and those right of its arrow,
type-only imports included; units sharing a row do not import each other. A new
top-level module or package, or one directly under `simulation/`, needs a row.
No row may link two of bunker, fleet, fuel and policy; economics or cohort to
bunker or policy; `parser` and `output`; or either to a simulation unit.

Inside `core/`, runtime imports run one way: `nodes/` imports `expectations/`,
`results/` and the flat modules directly in `core/`; `expectations/`,
`results/` and `general_nodes/` import only the flat modules; the flat modules
import no subpackage, and one that needs a node class imports it under
`TYPE_CHECKING`. The exception is `core/node_registry.py`, whose registries
read the classes of `nodes/` and `general_nodes/` at runtime, by design.
Imports are absolute (ruff `TID252`).

Nothing checks the layering mechanically; review holds it. A task that needs
the layering changed changes the table with the code.

## Data-flow invariants

- A value computed during the time loop that one of fleet, fuel, policy and
  bunker reads from another lives on the node's `expectation`: the computing
  domain writes it (`set_*`, `add_*`), the others read it (`get_*`). The one
  other path is `Simulation` handing a value on as a call argument, such as the
  multipliers a bunkering LP ran with to the policy functions settling it.
- The plain node attributes another domain reads are DSL inputs, what the
  lifecycle hooks derive from them (`Route.distinct_ports`), node maps, and two
  the first step's fleet initialization sets once and the bunkering LP reads:
  `Vessel.primary_fuel_type`, `Vessel.fleet_assignment`. The rest of a node's
  `# internal variables` group, such as `Fleet.increments`, is state its owning
  domain keeps for itself.
- A node map is written once, by `Simulation.initialize`, where it derives from
  DEFINE-only attributes, and every time step where events can change what it
  derives from.
- An expectation getter returns what its writer stored, or its default for a
  key never written, as `core` holds no model work: a quantity derived from
  stored values is computed in the domain that reads it, and where the parts of
  a sum are never read on their own, the writer stores the sum.
- `results` is output for the results file, never a decision's input. A step
  writes a result where it computes it; a result computed from other results is
  written after the run, once those are final, by the domain's `post_process`
  module or, for the global sums, `Simulation.finish`.
- `simulation/` handles no files, console output or arguments. Its one file
  output is an infeasible bunkering LP, written to the path `Simulation` is
  given, with its IIS beside it where the solver finds one.

## Node lifecycle

Steps 1 to 8 are the DEFINE pass of `Builder` (`parser/_build.py`); step 9
follows once. At every date, events or none, steps 2 to 8 run again, then 10:

1. `__init__(name)`: once per kept declaration.
2. The DSL setters: in DEFINE, the last assignment of each attribute; in an
   event, every assignment.
3. The parser raises where a `required=True` setter never ran for the node.
4. `initialize_dependencies(...)`, from `seed_dependencies` in
   `core/lifecycle.py`, the one method handed the registries.
5. The DSL commands: one call per command.
6. `build_table` on every table calculator, which builds a table set since
   the last pass.
7. The `initialize` sweep after DEFINE: `apply_defaults`, then
   `apply_command_defaults`; at each date, the `reinitialize` sweep: the
   latter only.
8. The `validate` sweep: `check_requirements`, then `check_consistency`.
9. `Simulation.initialize`: `initialize_expectation`, `initialize_results`.
10. `check_dynamic_consistency`: `Simulation`, at the start of each step.

`Node` (`core/node.py`) declares five hooks: `apply_defaults`,
`apply_command_defaults`, `check_requirements`, `check_consistency` and
`check_dynamic_consistency`; a node overrides these, never the `@final`
`initialize` and `reinitialize`. The three `initialize_*` methods are not
declared on `Node`; `seed_dependencies` and `Simulation` call them type by
type. `None` on a DSL input means unassigned; no DSL value is `None`. General
nodes take their assignments and the required-attribute check only.
