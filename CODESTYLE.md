<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Code Style

Ruff and mypy cannot check these conventions; `ruff format` owns layout within
statements. Where a convention and the configuration both speak, the
configuration wins. A per-file waiver in `.ruff.toml` is not an exception for
one package or file (`AGENTS.md`, Your role): it fits a rule to what its files
are for, as its comment, this file or `ARCHITECTURE.md` says, and excuses no
code that breaks the rule. Taste beyond these conventions follows the
`beautiful-code` skill in `.agents/skills/`.

## Naming

- Name parameters, variables and attributes descriptively, never by a single
  letter or an opaque prefix: `multipliers_total`, not `m`. The exceptions:
  - an integer index of a loop or comprehension (`i`, `j`, `k`, `t`);
  - the axis variables `x`, `y` of a table or interpolation;
  - the parameters of a DSL setter (see Nodes and the DSL);
  - an element or key variable whose letter the surrounding code gives one
    meaning: throughout `simulation/bunker/` the LP's subscripts keep the
    letters of the equations in its docstrings (`v` vessel, `p` port, `f`
    fuel, `c` converter).
- Reserve a bare `idx` for the time-step index, or for the slice of time steps a
  getter takes in its place, and qualify every other index: `vessel_idx`,
  `plant_idx`. Bound to a name, the slice from the time step onward is
  `forward = np.s_[idx:]`.
- Use domain words, not abbreviations: `newbuild_technology`, not `nb_tech`.
  Abbreviate only a term the DSL or the reference manual uses (`co2`, `lng`,
  `capex`, `wtt`).
- Name what a value means, not its container: `usable_fuels`, not
  `fuel_list`. No generic suffixes (`_data`, `_obj`, `_thing`).
- An underscored name is never used outside its scope (a module's is in
  `ARCHITECTURE.md`, Package map). The scope of a class or function is its
  module, widened to its package where the module is underscored too; that of
  an attribute or method is its class. `tests/`, which tests white-box, is
  exempt.
- Keep an external API's casing only where it is called, and bind the result
  to a snake_case name: `solution = self._highs.getSolution()`.
- If a function can only be named with "and", split it.

## Classes and attributes

- Define every instance attribute in `__init__` and annotate it there, never
  on the class body. Dataclass and `NamedTuple` fields, `Protocol` members,
  enum members and `ClassVar` constants are the exceptions.
- An attribute definition carries no trailing comment: what there is to say
  about one attribute is a why (see Comments) or belongs in the class
  docstring. A group comment may head a run of attributes. An enum member
  carries exactly one trailing comment, stating what it stands for.
- Read and write attributes directly: no method only returns or assigns an
  attribute, except the DSL setters, the expectation accessors and `.get`.
- A node class keeps an explicit `__init__(self, name)` that hands the name
  to its base, even where it does nothing else, so that every node is visibly
  constructed with its name. It calls `super().__init__(name)`; a calculator,
  which has a second base, calls `Node.__init__(self, name)` instead.
- A dictionary an expectation or results class holds as state gets its full
  key set at initialization and never allocates a key on first write, so a
  missing key fails loudly instead of growing the dictionary. A dictionary
  built as a local or a return value is outside the rule.

## Nodes and the DSL

- Every attribute a deck can assign on a node or general node, and every
  command it can call, lives in three places, each held by a test:
  - the node class: a DSL setter (`set_propulsion_load` on `Vessel`) marked
    `deck_attribute` or `deck_command` from `navigate/core/dsl.py` with the
    sections allowing it (`tests/unit/docs/test_setters_registered.py` fails
    on a `set_` or `add_` method without a mark);
  - its entry on the node's page in `docs/reference_manual/`, the only place
    it is explained to users (`tests/unit/docs/test_node_pages.py` fails on a
    page out of step with the marks either way);
  - one use in the attribute-coverage deck,
    `tests/end_to_end/simulations/attribute_coverage/`, which an agent keeps
    in step (`tests/AGENTS.md`; `tests/end_to_end/test_attribute_coverage.py`
    fails on a mark, or an ID value, the deck never uses).
- Lay out a node class under banners ruled with dashes to column 88:
  `# external variables` (what the deck sets) and `# internal variables` (what
  the model sets) in `__init__`, then `# external methods (DSL attributes)`,
  `# external methods (DSL commands)` and `# internal methods`. A setter's
  attribute sits in the external group of its class, except a table, which
  `set_table` holds in the internal `_pending_table` until `build_table` runs.
- Under `# internal methods`, order the lifecycle methods a node class defines
  `check_requirements`, `apply_defaults`, `apply_command_defaults`,
  `check_consistency`, `initialize_dependencies`, `initialize_expectation`,
  `initialize_results`, `check_dynamic_consistency`, and getters last.
- A DSL setter carries a docstring written for developers: one line naming
  what the setter stores, e.g. `"""Set the volumetric size of the tank."""`.
  It has no sections and states no units, limits, defaults, legal values or
  behaviour: those are written once, in its entry on the node's
  reference-manual page. A second paragraph holds only an implementation note
  the code cannot show. A `set_` method the model calls rather than the deck
  (`set_internal_bounds`) is no DSL setter and follows the Docstrings rules.
- A DSL setter's parameters are generic, as its name says what it sets: an
  attribute setter takes `value`, a command `key, value` or
  `key1, key2, value`. A local holding a converted key or value is named for
  what it holds (`energy_type`, `saving`).
- An attribute setter `set_x` stores `self.x`, `set_table` aside (above). A
  command sets one entry of a dictionary named for the collection, while the
  setter stays singular: in the plural where the noun is countable
  (`set_feed_constraint` writes `self.feed_constraints`), unchanged where it
  is a mass noun (`set_process_capex` writes `self.process_capex`).
- Deck-facing attribute names keep their DSL casing, Title case with acronyms
  as words (`Capex`, `LowerHeatingValue`), which `attribute_to_setter`
  (`navigate/util/naming.py`) splits at each capital into a setter name.
- Name the kinds a setter may be handed and store once, in
  `navigate/core/types_.py`, and use those aliases at every attribute
  definition and setter parameter. The alias matches the node types the
  setter passes as `type_=` to its `assign_*` call (`ScalarInput` for
  `type_=VARIABLE`). An attribute carries the storage kind (`*Input`), a
  setter parameter the argument kind (`*Argument`), which has `float` where
  the storage kind has `Scalar`, as the setter wraps it through `as_scalar`;
  `NumberInput` serves as both. An optional attribute still unset after
  construction is `<alias> | None`: never fold `None` into an alias, as `None`
  on a DSL input means unassigned.
- Where a kind a setter accepts breaks a method reading the attribute, the
  method handles that kind and the setter is not narrowed, as what a deck may
  write outranks a simpler setter: `simulation/fleet/power.py` handles an
  `Expression` propulsion load, which it cannot read as a table. Never
  evaluate an `Expression` as if it were a `Variable`, as it may wrap a
  `Curve` or `Forecast`.
- An attribute every deck must assign is marked `required=True` on its
  setter's `deck_attribute` decorator and declared in `__init__` by
  annotation alone, with no value and no `None`:
  `self.start_date: np.datetime64`. The parser checks it before anything reads
  it (`ARCHITECTURE.md`, Node lifecycle), so neither `check_requirements` nor
  any reader tests it again; `tests/AGENTS.md` has the test edits a newly
  required attribute brings. An internal attribute that a fixed
  initialization step sets before any reader runs is declared the same way
  (`self.primary_fuel_type: FuelTypeID`). One required only under a condition
  on other attributes stays `<alias> | None` and is tested in
  `check_requirements`.

## Dynamic state and results

- An expectation accessor takes its keys, outermost first, then the time
  step, the order a results field is indexed in; a setter or adder takes the
  value last: `set_bunker_wtt(fuel_name, emission_name, idx, wtt)` mirrors
  `get_bunker_wtt(fuel_name, emission_name, idx)`.
- An expectation getter reads one key or the whole storage, never either
  depending on its arguments: its key parameter has no default, and the
  whole-storage read is a separate getter, named in the plural where the
  keyed getter is singular. A time index may default to the full slice.
- The results classes (`navigate/core/results/`) are dataclasses written and
  read as plain fields, sharing the run-wide timeline, fuel and emission
  constants and the conversions by them in `ResultsContext`. A time step
  writes a result in the quantity it computed (a mass, a ton of each
  emission, a price per ton), for `post_process` to convert and combine
  (`ARCHITECTURE.md`, Data-flow invariants); a field `post_process` writes
  raises `AttributeError` if read before. The `result(unit)` declarations are
  the code's only record of the results and their units.
- Read the value of a calculator or a `Scalar` (`ARCHITECTURE.md`,
  Vocabulary) only through `.get`, which may take a variable number of inputs
  and may return a default or a pre-computed value. A table calculator's
  knots are no such value and are read directly, as its `.x` and `.y`:
  `ages = distribution.x[::-1]`.

## Typing

- Annotate a local variable only where mypy cannot infer its type, such as an
  empty container, a `None`-initialized accumulator, or a value from an
  untyped library.
- Annotate a parameter with what its callers pass: a union `X | Y` whose
  callers in `navigate/` all pass one arm narrows to that arm, and a test
  passing the other arm is carried like any signature change
  (`tests/AGENTS.md`).
- Never annotate a parameter `object` to avoid a type-only import the
  layering forbids; change what crosses the boundary instead:
  `navigate/exceptions.py` may not import a node, so `UnassignedAttributeError`
  takes `owner: str` and a node raises it with `str(self)`.

## Docstrings

Ruff `D` with the numpy convention decides where a docstring is required and
its section layout; the rules below cover the content.

- A `Parameters` section is optional; once present it lists every argument,
  each named without its type, which the signature carries, and described in
  one line where one line fits.
- `Returns` takes the numpydoc shape, a type line with the description
  indented under it: the type repeats the return annotation, as numpydoc
  requires a type for each return value.
- The docstring of a module that defines a class used outside its package
  says where the class is used.
- A class docstring states the responsibility of the class in one line, and
  `__init__` never carries a docstring. A class callers instantiate directly
  (`Scalar`, the calculators) adds a `Parameters` section describing the
  constructor arguments. A class only the framework constructs stays at one
  line; this covers every node except the calculators, as a node's inputs are
  DSL attributes documented in the reference manual.
- A node's lifecycle methods and the methods of expectation classes need no
  docstring. Ruff `D102` is waived for `nodes/`, `general_nodes/` and
  `expectations/` under `navigate/core/` to allow that, so nothing flags a
  DSL setter that lacks its docstring.

## Comments

- Write a comment only for a why the code cannot show; by default write none,
  and never restate the code.
- A comment reads correctly to someone who never saw another version: it is
  never framed against a previous version or a rejected alternative, and
  never says when or for which change the code was written (a date, "added
  for the X flow").
- Start a comment with a lowercase letter, unless its first word is an
  identifier, acronym or proper noun spelled with a capital.
- In an `if`/`elif` chain, a comment on why the branching exists goes above
  the `if`; a comment on one branch is the first line inside that branch.
- Write comments and docstrings in plain ASCII: `-` for a dash, `->` for an
  arrow, straight quotes. User-facing message strings (errors, log messages)
  and licence header lines are exempt, though ruff flags a confusable such as
  `–` or `’` in any string.

## Layout

- Blank lines separate logical sections; statements forming one conceptual
  operation stay adjacent. In particular:
  - A guard clause (a short `if` ending in `return`, `continue`, `break` or
    `raise`) is followed by a blank line.
  - Logging calls, and statements that build a message for them, form their
    own section, with a blank line above and below.
  - The end of a block is no section break by itself: a block that belongs
    to the operation around it, such as a lookup loop or an `if`/`else`
    choosing one value, is followed directly by the next statement. After a
    block that carries out a step of its own, a blank line starts the next
    section.
- Define the locals an operation needs together before it, not between its
  steps.

## Numerics

- State a physical quantity's unit in the docstring entry of the parameter or
  return value it applies to, written `<description>, in <unit>.`: `Fuel
  price, in USD/GJ.` DSL setters are exempt; their units live in the reference
  manual.
- Test a computed float for zero or for equality within a named tolerance
  constant (`TOLERANCE` in `navigate/util/numeric.py`), through `abs`,
  `math.isclose` or `np.isclose`, so that a rounding residual takes the same
  branch as an exact zero: `abs(multiplier) < TOLERANCE`,
  `abs(power_to - power_from) > TOLERANCE`. Exact `==`/`!=` is allowed
  against an assigned value (a default, a sentinel, a deck input), on a value
  rounded to `ROUND_OFF`, and for a guard that only protects an operation
  undefined at zero, such as a division.

## Validation and dynamic access

- Validate deck input in the `assign_*` functions (`navigate/core/assign.py`)
  the setters call and in the `check_*` hooks. An error names the node, the
  attribute and the offending value; an `assign_*` error leaves the node and
  attribute to the parser. `calculate_*` and expectation methods contain no
  checks; past validation, trust the types.
- Reject at validation any input that leaves the model without meaning, and
  never guard against it where it is used, as a guard at each use spreads a
  default through the model: `set_vessels` takes at least one vessel, so no
  reader meets a fleet without vessels. A zero a valid run reaches, such as
  the energy of a vessel that spent none, is guarded where it arises
  (Numerics; `divide_nonzero` in `navigate/util/numeric.py`).
- Check a rule relating attributes an event can assign in
  `check_consistency`, or in `check_requirements` where it decides whether
  one is required (Nodes and the DSL), never in a setter: an event assigns
  one attribute at a time, so attributes that must agree are out of step while
  a date's assignments run. A calculator's `LowerBound` and `UpperBound` may
  cross between two assignments; its `check_consistency` rejects bounds that
  admit no value. A command may check its input against a DEFINE-only
  attribute, which is set before any command runs and never changes after
  (`ARCHITECTURE.md`, Node lifecycle).
- In `navigate/`, confine dynamic attribute access (`hasattr`, `getattr`,
  `setattr`, `delattr`, `vars`, `__dict__`) to the boundary modules:
  `navigate/parser/` (DSL dispatch), `navigate/output/` (results by name) and
  `navigate/app/` (the `extra` keys of a log record). The exception is
  `navigate/core/dsl.py`, which uses `vars` to collect decorator marks from
  methods defined on a class and its bases.

## Logging

- A module logs through a module-level `logger = logging.getLogger(__name__)`
  and imports nothing from `navigate` to log, as `RunLog` alone configures
  logging.
- Pass a heading or a table through `extra` (`heading=True`, `table={column
  name: values}`) for `RunLog` to frame or render, never assembled into the
  message.
