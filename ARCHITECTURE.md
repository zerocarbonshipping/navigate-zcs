<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Architecture

Navigate simulates the maritime transition as two decision-making domains —
shipowners (`simulation/fleet/`) and fuel producers (`simulation/fuel/`) —
built on shared foundations and coordinated per time step by `Simulation` in
`simulation/time_stepping.py`, which `driver/` runs from a read deck to its
output. The domains never import each other: they interact only through
`core` expectations and the bunkering LP. This file maps the code; the DSL
and model behavior are documented in `docs/reference_manual/`.

## Package map

- `simulation/` — the model: `time_stepping.py`'s `Simulation` initializes
  the nodes' dynamic state, performs one date's time step in a fixed phase
  order and post-processes the run into its `SimulationResults`; pure
  orchestration: each phase calls an entry point of a domain subpackage.
  - `simulation/fleet/` — the shipowner domain: voyage physics and energy
    demand, valuation (charter rates, technology package calculations,
    marginal-saving heuristics) and the speed, technology, fuel-conversion
    and newbuild/scrap decisions.
  - `simulation/fuel/` — the fuel-supply domain: production and delivery
    economics, supply/demand balancing, port fuel supply, and producer
    capacity planning.
  - `simulation/economics/` — asset-agnostic valuation-and-choice toolkit
    (cash flows, NPV/levelized cost, discrete choice) used by both domains.
  - `simulation/bunker/` — the per-time-step bunkering LP: build → solve →
    transfer.
  - `simulation/policy/` — regulation/levy emission coefficients,
    jurisdiction attribution, and regulation flexibility-cost beliefs.
- `core/` — the model definition, and nothing else: the DSL value types and
  their semantics (assignment validation, table interpolation, calculator
  bounds, forecast precalculation, expression evaluation); the node classes
  (`core/nodes/`, one per DSL keyword), the singleton general nodes
  (`core/general_nodes/`) and the maps between nodes derived from static
  node attributes (`node_maps.py`); the state attached to nodes,
  `expectations/` (cross-module dynamic state) and `profiles/` (end-of-run
  output containers); the records nodes hold (`increment.py` asset cohorts,
  `technology_package.py`); and the `SimulationResults` record a finished
  run hands to output (`simulation_results.py`).
- `parser/` — reads `.nav`/`.inc` decks into nodes (Lark grammar).
- `output/` — turns a run's `SimulationResults` into Excel/CSV reports and
  figures; `output/plots/` renders the latter.
- `util/` — dependency-free helpers: collections, dates, naming, numerics,
  internal types and unit conversion factors; imports nothing from
  `navigate` outside `util/`.
- `driver/` — the run sequence: `run.py` reads a deck, steps the
  `Simulation` through its dates with each date's events applied first, and
  writes the reports and plots.
- `app/` — the interfaces Navigate is run through: `logs.py`, the run log
  of a CLI run (its log file, line format, warning ledger and summary) and
  the console preamble.
- `exceptions.py` — the `NavigateError` hierarchy; `__main__.py` — the CLI,
  which runs a deck through `driver/`.

## Domains

A domain lives in four places: its node classes in `core/nodes/`, their
expectations in `core/expectations/`, their profiles in `core/profiles/`,
and its calculations in `simulation/<domain>/`.

| Domain      | `core/nodes/`                        | `core/expectations/`                                                     | `core/profiles/`                                             | Calculations            |
| ----------- | ------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------ | ----------------------- |
| `fleet`     | `fleet.py`, `vessel.py`              | `fleet_expectation.py`, `vessel_expectation.py`                          | `fleet_profile.py`, `vessel_profile.py`                      | `simulation/fleet/`     |
| `fuel`      | `producer.py`, `plant.py`, `port.py` | `producer_expectation.py`, `plant_expectation.py`, `port_expectation.py` | `producer_profile.py`, `plant_profile.py`, `port_profile.py` | `simulation/fuel/`      |
| `economics` | —                                    | —                                                                        | —                                                            | `simulation/economics/` |
| `bunker`    | —                                    | —                                                                        | —                                                            | `simulation/bunker/`    |
| `policy`    | `regulation.py`, `levy.py`           | `regulation_expectation.py`, `levy_expectation.py`                       | `regulation_profile.py`, `levy_profile.py`                   | `simulation/policy/`    |

The node classes not listed are inputs any domain reads, and the private
modules beside the listed ones hold their shared bases. `global_profile.py`
is `Simulation`'s own.

Node classes hold state, and domain calculations live in `simulation/`. The
per-node calculations below still sit on the node classes in `core/nodes/`;
the list must not grow:

- `calculate_expectation` and `calculate_profile` on `Port`, `Regulation`
  and `Vessel`, and `Levy.calculate_expectation`;
- `_Policy._calculate_policy_expectations`, the global warming potentials
  of both policies' expectations;
- the ageing: `_AssetManager.update_increment_ages` and
  `_AssetManager._age_increments`, which `Producer` overrides;
- the initial cohorts: `_AssetManager.define_initial_age` and
  `_AssetManager.define_initial_multipliers`, with the hooks `Fleet` and
  `Producer` override, and `Producer.define_initial_decided`;
- `Route._normalize_voyage_distribution`, the voyage normalisation;
- `Converter.get_effective_lhv`, the heating value net of slip.

## Layering

```
util, __init__, simulation               → (nothing)
exceptions                               → util
core                                     → foundation
simulation.economics, simulation.policy  → core, foundation
simulation.fleet, simulation.fuel        → simulation.economics, core, foundation
simulation.bunker                        → simulation.policy, core, foundation
parser, output                           → core, foundation
app                                      → foundation
simulation.time_stepping                 → simulation.economics, simulation.policy,
                                           simulation.fleet, simulation.fuel,
                                           simulation.bunker, core, foundation
driver                                   → simulation.time_stepping,
                                           simulation.economics, simulation.policy,
                                           simulation.fleet, simulation.fuel,
                                           simulation.bunker, parser, output,
                                           core, foundation
__main__                                 → driver, app, core, foundation
```

A unit is a package or module under `navigate/` with a row, named by its
dotted path; `__init__` is `navigate/__init__.py`. A file belongs to the
longest unit that contains it. A unit imports itself and the units in its
row, and nothing else from `navigate`. The foundation is `util/` and
`exceptions.py`.

`simulation.fleet` and `simulation.fuel` never import each other, and
`parser`, `output` and the simulation (`simulation/` and everything under
it) never import one another.

`simulation` is a unit of its own: `simulation/__init__.py`, which imports
nothing. A package that only groups other modules and subpackages keeps an
empty `__init__.py`, and `simulation/` is one: re-exporting `Simulation` or
the domains' entry points there would load every domain on any import from
the package, and with `simulation/bunker/` the Gurobi licence probe that
`solver.py` runs at import.

Inside `core/`, runtime imports follow an order: `nodes/` imports
`expectations/`, `profiles/` and the flat modules directly in `core/`,
`core/__init__.py` included; `expectations/`, `profiles/` and
`general_nodes/` import only the flat modules; the flat modules import only
one another. Each subpackage also imports itself.

Imports inside `navigate` are absolute, so `tests/unit/test_layering.py`,
which rejects relative ones, sees every import. It enforces all of this,
type-only imports included except for the order inside `core/`. Its tables
are exact and acyclic: every file belongs to a unit, every unit exists on
disk, and the order inside `core/` names every directory directly in
`core/` (a deeper one belongs to the subpackage that contains it) and
nothing else.

## Logging

Records propagate from the module loggers to the root logger. `RunLog` in
`app/logs.py` is the only code that configures logging, and the CLI holds
it open for the whole run. It owns the log file's handler on the root
logger; the ledger, a filter on that handler that counts every record per
level and writes a repeated warning once; and the formatter. The formatter
reads two optional record attributes, the contract an emitter passes
through `extra`: `heading=True` frames the message in horizontal rules, and
`table={column name: values}` renders the columns as a table under the
message.

## Data-flow invariants

- Dynamic results that cross modules flow through the node's `expectation`:
  the computing module writes via `set_*`/`add_*`, everyone else reads via
  `get_*`.
- `profile` is output storage for end-of-simulation reports and plots; it is
  never read as an input to a simulation decision. Inside the
  profile-aggregation phase (`Simulation._calculate_profile`) and
  post-processing, deriving one profile value from an already-written one is
  fine — nothing downstream of those phases feeds a decision.
- Direct attribute access (`node.some_input.get()`) is reserved for
  DSL-defined inputs.
- `simulation/` handles no files, console output or arguments; its one file
  write is the bunker's infeasible-LP dump into the directory it is given.

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
  part of `initialize()`/`reinitialize()`: `Simulation` calls it once per
  time step, before the expectations, over `timeline[idx:]` and
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

- `simulation/fleet/` and `simulation/fuel/` mirror each other deliberately
  (`initialization.py`, `evolution.py`, `planning.py`, `aggregation.py`):
  same name, same role in each domain.
- A leading underscore on a module or class means package-private; anything
  used across package boundaries carries a public name.
- Each package's `__init__.py` re-exports its externally consumed entry
  points — read it first to learn the package's API. A package that only
  groups others, such as `simulation/`, keeps it empty (see Layering).
