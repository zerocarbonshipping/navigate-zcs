<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Architecture

Navigate simulates the maritime transition as two decision-making domains,
shipowners (`simulation/fleet/`) and fuel producers (`simulation/fuel/`),
which interact only through `core` expectations and the bunkering LP.
`Simulation` in `simulation/time_stepping.py` coordinates them per time
step, and `driver/` runs it from a read deck to its output.

## Package map

- `simulation/` — the model. `Simulation` does no model work of its own: it
  orchestrates the domains in a fixed phase order.
  - `simulation/fleet/` — the shipowner domain: operation and decisions.
  - `simulation/fuel/` — the fuel-supply domain: production and planning.
    The two mirror each other: `initialization.py`, `evolution.py`,
    `planning.py` and `aggregation.py` play the same role in each.
  - `simulation/economics/` — valuation and choice used by both domains.
  - `simulation/bunker/` — the per-time-step bunkering LP.
  - `simulation/policy/` — policy emission coefficients and beliefs.
- `core/` — the model definition only: the DSL value types and their
  semantics, the node classes (`nodes/`, one per DSL keyword), the general
  nodes (`general_nodes/`), the node maps, `expectations/`, `profiles/`, the
  records nodes hold, and the `SimulationResults` a run hands to output.
- `parser/` — reads `.nav`/`.inc` decks into nodes (Lark grammar).
- `output/` — turns `SimulationResults` into reports and figures (`plots/`).
- `util/` — domain-agnostic helpers.
- `driver/` — the run: read a deck, step `Simulation`, write the output.
- `app/` — the command line (`cli.py`) and its run log (`logs.py`), whose
  `RunLog` is the only code that configures logging.
- `exceptions.py` — the `NavigateError` hierarchy; `__main__.py` runs `app`.

## Domains

A domain's node `x.py` in `core/nodes/` keeps its cross-module dynamic state
in `core/expectations/x_expectation.py` and its output in
`core/profiles/x_profile.py`; the domain's calculations live in
`simulation/<domain>/`. The fleet domain owns `Fleet` and `Vessel`, fuel
owns `Producer`, `Plant` and `Port`, and policy owns `Regulation` and
`Levy`. `simulation/economics/` owns no nodes, and `simulation/bunker/`'s
settings are the general node `core/general_nodes/bunker_options.py`.

Node classes hold state, and the calculators among them (`Curve`,
`Forecast` and the like) their value semantics; model work lives in
`simulation/`. The node methods below are a known exception, and the list
must not grow:

- `calculate_expectation` on `Port`, `Regulation`, `Vessel` and `Levy`,
  `calculate_profile` on the first three, and
  `_Policy._calculate_policy_expectations`;
- `_AssetManager`'s `update_increment_ages`, `_age_increments`,
  `define_initial_age` and `define_initial_multipliers`, with the hooks
  `Fleet` and `Producer` implement for them, and
  `Producer.define_initial_decided`;
- `Route._normalize_voyage_distribution`.

## Layering

```
util, __init__, simulation         → (nothing)
exceptions                         → util
core                               → foundation
simulation.economics               → core, foundation
simulation.policy                  → core, foundation
simulation.fleet, simulation.fuel  → simulation.economics, core, foundation
simulation.bunker                  → simulation.policy, core, foundation
parser, output                     → core, foundation
app                                → driver, foundation
simulation.time_stepping           → domains, core, foundation
driver                             → simulation.time_stepping, domains,
                                     parser, output, core, foundation
__main__                           → app
```

A unit is a package or module under `navigate/` with a row, named by its
dotted path; `__init__` is `navigate/__init__.py` and `simulation` is
`simulation/__init__.py` alone. A file belongs to the longest unit that
contains it; a unit imports itself and its row, nothing else from
`navigate`. The foundation is `util/` and `exceptions.py`; the domains are
the five `simulation.<domain>` units. Every file must fall in a unit, so a
new top-level module or package needs a row here and in the test's
`LAYERS`. No row may link `simulation.fleet` and `simulation.fuel`,
`parser` and `output`, or either of those two and a simulation unit.

Inside `core/`, runtime imports run one way: `nodes/` imports
`expectations/`, `profiles/` and the flat modules directly in `core/`;
`expectations/`, `profiles/` and `general_nodes/` import only the flat
modules; the flat modules import no subpackage, so one that needs a node
class imports it under `TYPE_CHECKING`. Imports are absolute.
`tests/unit/test_layering.py` enforces the table with type-only imports
included, and the order inside `core/` for runtime imports only.

Each package's `__init__.py` re-exports its externally consumed entry
points; read it first. `simulation/`, `core/nodes/`, `core/general_nodes/`
and `output/plots/` keep it empty and importers name the module, as a
re-export there would load far more than an import needs.

## Data-flow invariants

- Cross-module dynamic results flow through the node's `expectation`: the
  computing module writes (`set_*`, `add_*`), the others read (`get_*`).
- `profile` is output for reports and plots, never a decision's input.
  Deriving one profile value from another is fine in post-processing and
  `Simulation._calculate_profile`, which feed no decision.
- Direct attribute access (`node.some_input.get()`) is reserved for
  DSL-defined inputs.
- `simulation/` handles no files, console output or arguments; its one file
  write is the bunker's infeasible-LP dump into the directory it is given.

## Node lifecycle

`Node` in `core/node.py` has two `@final` entry points the parser calls,
`initialize()` and `reinitialize()`, which run the hooks; a node overrides
the hooks only, each documented there with its role and cadence.
`Simulation`, not the parser, calls `check_dynamic_consistency` once per
time step. The parser checks the attributes every deck must assign, listed
in `parser/_attributes.py`, before `initialize_dependencies(...)` and the
hooks run. `None` on a node attribute means unassigned; no DSL value is
`None`. What derives from the node registries, and the seeding of the
command-written dictionaries before the commands run, goes in
`initialize_dependencies(...)`, the only method the parser hands them. It
runs before the commands on every pass, DEFINE and each event read, so it
seeds with `setdefault` and recomputes what it derives. General nodes take
DEFINE attributes only and have no hooks.
