<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Architecture

Navigate simulates the maritime transition as two sides that decide,
shipowners (`simulation/fleet/`) and fuel producers (`simulation/fuel/`),
which interact only through `core` expectations and the bunkering LP.
`Simulation` in `simulation/time_stepping.py` steps them through the dates of
a deck, and `driver/` runs it from the deck to the results file.

## Vocabulary

- Deck: a `.nav` or `.unc` file of one DEFINE and one EVENTS section, with
  the `.inc` files it includes; `parser/grammar.lark` holds the grammar.
- Node: an instance of a `Node` subclass in `core/nodes/` (one class per DSL
  keyword), one per kept declaration of a type and name, held in `Nodes`
  (`core/node_registry.py`).
- General node: `ModelDefinition` or `BunkerOptions` (`core/general_nodes/`),
  one of each per run, unnamed, built from all its blocks (`BunkerOptions` by
  default where there are none), with DEFINE attributes only, no commands and
  no lifecycle hooks.
- Calculator: a node evaluated through `.get`: `Curve`, `Forecast`,
  `Surface`, `Timetable`, `Variable` (`CALCULATOR_TYPES` in
  `core/node_type.py`); a `Scalar` (`core/scalar.py`) may stand in for one.
- Expectation: `node.expectation` (`core/expectations/`), the dynamic state
  of a Fleet, Levy, Plant, Port, Producer, Regulation or Vessel over the
  timeline, behind `set_*`, `add_*` and `get_*` accessors.
- Results: `node.results`, a dataclass in `core/results/`, and the run-wide
  `GlobalResults`: what the results file reports, the fields declared with
  `result(unit)`.
- Node map: a node attribute derived from other nodes' attributes, such as
  `Vessel.usable_fuels`, written by `core/node_maps.py` only.
- Cohort: the assets of one age bin, an `Increment` (`core/increment.py`):
  in service in `Fleet.increments` and `Producer.increments`, awaiting
  delivery in `Producer.pipeline`; `simulation/cohort.py` is their shared
  accounting.
- DEFINE and EVENTS: DEFINE declares the nodes. An event is a node body in
  EVENTS under `Start` or a `Date`, applied at that date to declared nodes,
  through setters and commands marked `SECTION_BOTH` (`core/dsl.py`) rather
  than `SECTION_DEFINE`. The dates are the start date and every `Date`.
- Time: `Simulation.timeline` holds days since the start date, and a step's
  size, from the date before (`Simulation._time_step_at`), is in days, the
  first taken as one year (`YEAR`). Ages are in years (`Increment`), as is the
  `ResultsContext` timeline; the results file divides a `per_step` result by
  its step length in years (`step_lengths`), to a per-year rate.
- Default library: the assumptions folder (`-d` or `ASSUMPTIONS_DATA_DIR`),
  with default nodes at `defaults/<NodeType>/<name>.inc` and modules at
  `modules/<module>.inc` (`parser/_library.py`).
- Bunkering LP: the allocation of fuel to vessels at ports
  (`simulation/bunker/`), run as two `BunkerAlgorithm`s: the existing scope
  solves the current step for the fleet as it stands, the expected scope
  every step to the horizon for the decisions.
- Domain: one of the five packages under `simulation/`: `fleet`, `fuel`,
  `policy`, `bunker` and `economics`. Fleet and fuel are the two sides.
- Unit: in the layering, a package or module under `navigate/` with a row in
  the table, named by its dotted path.

## A run, end to end

1. `main` in `app/cli.py` (the `navigate` command) reads the arguments, opens
   a `RunLog` (`app/logs.py`) and calls `run_deck` in `driver/run.py`, which
   the test suites also call.
2. `Parser.read_deck` (`parser/parser.py`) reads the deck in four phases,
   each finished before the next starts:
   1. Collect (`_collect.py`): the deck's files become declarations, one
      node's body items in read order, and events. `_params.py` fills each
      file's `%NAME%` placeholders and `_syntax.py` parses it into the AST
      the later phases read; `_library.py` looks up the default-library file
      of each module the deck loads and each name it imports, or copies or
      references without declaring it.
   2. Resolve (`_resolve.py`): each event is bound to the declarations it
      targets.
   3. Prune (`_prune.py`): the references from `ROOT_TYPES` decide the
      declarations the simulation holds; no other is ever constructed. Then
      `check_pinned_calculators`, in `_resolve.py`, refuses an event
      changing a calculator a kept node's DEFINE-only input holds.
   4. Build (`_build.py`): the general nodes first, as the dates count from
      the start date in `ModelDefinition`, then one node per kept
      declaration, through the DEFINE pass of the node lifecycle.
3. `Simulation` refuses a deck without a Fleet or a Fuel (`check_runnable`);
   `Simulation.initialize` writes the node maps that derive from DEFINE-only
   attributes, sizes the expectations and results to the timeline and builds
   the two bunkering LPs.
4. For each date, `Parser.read_events` applies the date's events, and
   `Simulation.step` runs the time step, told whether any statement applied.
5. `Simulation.finish` has the `post_process` modules of fleet, fuel and
   policy complete the results, vessels before fleets, and returns the
   `GlobalResults`.
6. `run_deck` wraps them, with the nodes, in `SimulationResults`, and
   `write_results` (`output/results_writer.py`) writes the Parquet file.

### One time step

`Simulation._perform_time_step` in `simulation/time_stepping.py` holds the
exact order of a step; read it there. Its shape:

1. Every node's `check_dynamic_consistency`, the node maps events can
   change, and forecasts and timetables set to the step's time.
2. The step's expectations and the vessels' operations; the plant
   production and logistics expectations at the first step and after events.
3. At the first step only, the existing fleet and production.
4. The policy emission coefficients and the vessels' asset charter.
5. From the second step on, evolution (`_perform_evolution`): the
   expected-scope LP gives the outlook the shipowners, then the producers,
   decide on.
6. The fuel imports to ports, then the existing-scope LP
   (`_perform_existing_bunkering`), which allocates the step's fuel to the
   fleet as it then stands; policy settles compliance, remedial expenses
   and flexibility markets on it.
7. The fleet's fuel-type balance, then the step's results recorded.

The expected scope runs before the decisions it informs and the existing
scope after them, each on inputs recalculated just before it, so the step's
fuel goes to the fleet those decisions left.
The emission coefficients are computed once for both scopes, as nothing they
read changes later in the step.

## Package map

- `simulation/`: the model; `Simulation` orchestrates and does no model
  work of its own.
  - `fleet/` owns `Fleet` and `Vessel`, `fuel/` owns `Producer`, `Plant`
    and `Port`, `policy/` owns `Regulation` and `Levy`. Each such node `x.py` in
    `core/nodes/` keeps its expectation in
    `core/expectations/x_expectation.py` and its results in
    `core/results/x_results.py`; its calculations live in its owning domain.
  - `bunker/` owns no node; its settings are the general node
    `BunkerOptions`. It reads the LP's regulation inputs from the
    expectations `policy/` writes and transfers the solution (`_transfer/`).
  - `economics/` (valuation and choice) and `cohort.py` serve fleet and fuel.
- `core/`: the model definition only: node classes, which hold state and,
  for the calculators, value semantics; `expectations/`; `results/`; flat
  modules for the DSL values, the registries, the sweeps and the node maps.
- `parser/` (its grammar in `grammar.lark`),
  `output/`, `driver/`, `app/` (its `RunLog` alone configures logging),
  `util/` and `exceptions.py`, as their docstrings say.

Fleet, fuel and policy share a file layout: `initialization.py` (fleet and
fuel only) sets up the starting fleet or production at the first step,
`expectation.py` writes what later phases and other domains read,
`results.py` records results at the end of each step, and `post_process.py`
computes the results derived from those after the run. Every other module is
named for a concept of the domain.

A package's public names are what its `__init__.py` re-exports, and code
outside the package imports them from the package, not from the module. A
module or subpackage with a leading underscore is imported only inside its
package; in the domains, a module is underscored where the package
re-exports nothing from it. `core/` and `util/` re-export only part:
`util.types_`, and the `core` modules and names `core/__init__.py` leaves
out (`core.enum_`, `core.node_registry`, `core.types_`), are imported by
module path. Six `__init__.py` files hold a docstring only, four of them
because a re-export would load far more than an import needs: `navigate/`
and `simulation/` run before any import of a module below them, and in
`core/nodes/` and `core/general_nodes/` importing one node class would load
all of them. In the other two, `simulation/bunker/_constraints/` and
`_transfer/`, the bunker modules import each module by name.

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

`__init__` is `navigate/__init__.py` and `simulation` is
`simulation/__init__.py` alone; the foundation is `util/` and
`exceptions.py`, and `domains` the five domains. A file belongs to the
longest unit that contains it. A unit imports itself and the units right of
the arrow in its row, nothing else from `navigate`, type-only imports
included; units sharing a row do not import each other. Every file must fall
in a unit, so a new top-level module or package, or a new module or package
directly under `simulation/`, needs a row. No row may link two of the
domains bunker, fleet, fuel and policy, nor link economics or cohort to
bunker or policy, nor link `parser` and `output`, nor link either of them to
a simulation unit.

Inside `core/`, runtime imports between its parts run one way: `nodes/`
imports `expectations/`, `results/` and the flat modules directly in
`core/`; `expectations/`, `results/` and `general_nodes/` import only the
flat modules; the flat modules import no subpackage, and one that needs a
node class imports it under `TYPE_CHECKING`. The exception is
`core/node_registry.py`, whose registries read the classes of `nodes/` and
`general_nodes/` off their annotations at runtime, by design. Imports are
absolute.

Nothing checks the layering mechanically; review holds it. A task that needs
the layering changed changes the table with the code.

## Data-flow invariants

- A value computed during the time loop that one of fleet, fuel, policy and
  bunker reads from another lives on the node's `expectation`: the computing
  domain writes it (`set_*`, `add_*`), the others read it (`get_*`). As the
  four import none of one another, `core` is where they meet. The one other path
  is `Simulation` handing a value on as a call argument, such as the
  multipliers a bunkering LP ran with to the policy functions settling it.
- The plain node attributes another domain reads are DSL inputs, what the
  lifecycle hooks derive from them (`Route.distinct_ports`), node maps, and
  two the first step's fleet initialization sets once and the bunkering
  LP reads: `Vessel.primary_fuel_type`, `Vessel.fleet_assignment`. The rest
  of a node's `# internal variables` group, such as `Fleet.increments`, is
  state its owning domain keeps for itself.
- A node map is written once, by `Simulation.initialize`, where it derives
  from DEFINE-only attributes, and every time step where events can change
  what it derives from.
- An expectation getter returns what its writer stored, or its default for
  a key never written, as `core` holds no model work: a quantity derived from
  stored values is computed in the domain that reads it, and where the parts
  of a sum are never read on their own, the writer stores the sum.
- What `_recalculate_derived_expectations` writes reads no simulation state
  and evaluates every calculator at an explicit time, as it is recalculated
  only at the first step and after events.
- `results` is output for the results file, never a decision's input. A step
  writes a result where it computes it; a result computed from other results
  is written after the run, once those are final, by the domain's
  `post_process` module or, for the global sums, `Simulation.finish`.
- `simulation/` handles no files, console output or arguments. Its one file
  output is an infeasible bunkering LP, written to the path `Simulation` is
  given, with its IIS beside it where the solver finds one.

## Node lifecycle

Steps 1 to 8 are the DEFINE pass of the parser's `Builder`
(`parser/_build.py`), and step 9 follows once. At every date, events or
none, steps 2 to 8 run again, before that date's step 10:

1. `__init__(name)`: once per kept declaration.
2. The DSL setters: in DEFINE, the last assignment of each attribute; in an
   event, every assignment.
3. The required-attribute check: the parser raises where a setter marked
   `required=True` never ran for the node, before anything reads it.
4. `initialize_dependencies(...)`, from `seed_dependencies` in
   `core/lifecycle.py`: the one method the parser's passes hand the
   registries. It seeds the dictionaries the commands write and computes
   what derives from the registries; as it runs before the commands on every
   pass, it seeds with `setdefault` and recomputes what it derives.
5. The DSL commands: one call per command.
6. `build_table` on every table calculator, which builds a table set since
   the last pass.
7. After DEFINE, the `initialize` sweep: `Node.initialize()` runs
   `apply_defaults()`, then `apply_command_defaults()`. At each date, the
   `reinitialize` sweep: `Node.reinitialize()` runs
   `apply_command_defaults()` only.
8. The `validate` sweep: `check_requirements()`, then `check_consistency()`.
9. `initialize_expectation(...)`, then `initialize_results(...)`:
   `Simulation.initialize`.
10. `check_dynamic_consistency(times, dates)`: `Simulation`, at the start of
    each time step.

`Node` (`core/node.py`) declares five hooks, each documented with its role
and cadence: `apply_defaults`, `apply_command_defaults`,
`check_requirements`, `check_consistency` and `check_dynamic_consistency`. A
node overrides these, never the `@final` `initialize` and `reinitialize`.
`initialize_dependencies`, `initialize_expectation` and `initialize_results`
are not declared on `Node`: a class that needs one defines it with the
registries or sizes it takes, and `seed_dependencies` and `Simulation` call
it type by type. `check_requirements` and `check_consistency` run nowhere
but the `validate` sweep. `None` on a DSL input means unassigned; no DSL
value is `None`. General nodes take their assignments and the
required-attribute check only.
