<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Code Style

This document holds the conventions that ruff (`.ruff.toml`) and mypy
(`mypy.ini`) cannot check; `ruff format` owns the layout within statements, a
parenthetical names a check covering part of a rule, and the configuration is
the arbiter where both speak. A convention found wrong is changed here and in
the code it governs in one commit, repository-wide, never as an exception for
one package or file (`AGENTS.md`, Your role). The per-file waivers in
`.ruff.toml` are no such exceptions: each fits a rule to what those files are
for, as its comment, this document or `ARCHITECTURE.md` says, and none excuses
code that breaks a rule. Taste beyond these conventions is the writer's.

## Naming

- Name functions, methods, variables and attributes in snake_case with
  acronyms lowercased: `set_fuel_wtt`, `self.fuel_wtt` (ruff `N` checks every
  name except an attribute assigned on an object).
- Give parameters, variables and attributes descriptive names, not single
  letters or opaque prefixes: `multipliers_total`, not `m` (ruff `E741` flags
  only `l`, `O`, `I`). Exempt are an integer index of a loop or comprehension
  (`i`, `j`, `k`, `t`), but not an element or key variable, the axis variables
  `x`, `y` of a table or interpolation, and the parameters of a DSL setter
  (see Nodes and the DSL).
- Reserve a bare `idx` for the time-step index, or for the slice of time steps a
  getter takes in its place, and qualify every other index: `vessel_idx`,
  `plant_idx`. Bound to a name, the slice from the time step onward is
  `forward = np.s_[idx:]`.
- Use domain words, not abbreviations: `newbuild_technology`, not `nb_tech`.
  Abbreviate only a term the DSL or the reference manual uses (`co2`, `lng`,
  `capex`, `wtt`).
- Name what a value means, not its container: `usable_fuels`, not
  `fuel_list`. No generic suffixes (`_data`, `_obj`, `_thing`).
- Phrase boolean names positively: `is_flexible`, not `is_not_flexible`.
- Reserve ALL_CAPS for enum members (`AMMONIA`, `FLAT`), module-level
  constants and `ClassVar` constants (ruff `N802`, `N803` and `N806` flag it
  on a function, an argument and a local).
- An underscored name is never used outside its scope (a module's is in
  `ARCHITECTURE.md`, Package map): a class or function outside its module
  (outside its package when the module is underscored too), an attribute or
  method outside its class. Use from `tests/`, which tests white-box, does not
  count (ruff `SLF001` flags `obj._name` unless `obj` is `self`, `cls` or
  typed as the enclosing class).
- Keep an external API's casing only where it is called, and bind the result
  to a snake_case name: `solution = self._highs.getSolution()`.
- If a function can only be named with "and", split it.

## Classes and attributes

- Define every instance attribute in `__init__` and annotate it there, never
  on the class body. Dataclass and `NamedTuple` fields, `Protocol` members,
  enum members and `ClassVar` constants are the exceptions (ruff `RUF012`
  flags only a mutable class-body value not annotated `ClassVar`).
- An attribute definition carries no trailing comment. What there is to say
  about one attribute is either a why (see Comments) or belongs in the class
  docstring. A group comment heading a run of attributes is allowed. An enum
  member carries exactly one trailing comment, stating what it stands for.
- Read and write attributes directly. Do not add a method that only returns
  or assigns an attribute, except the DSL setters, the expectation accessors,
  and `.get`.
- A dictionary an expectation or results class holds as state gets its full
  key set at initialization and never allocates a key on first write, so a
  missing key fails loudly instead of growing the dictionary. A dictionary
  that code builds as a local or return value, by a loop or a comprehension,
  is outside the rule.

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
  `initialize_results`, `check_dynamic_consistency`, and getters last
  (`ARCHITECTURE.md`, Node lifecycle, says which five are hooks on `Node`).
- A DSL setter carries a docstring written for developers: one line naming
  what the setter stores, e.g. `"""Set the volumetric size of the tank."""`.
  It has no `Parameters` or `Examples` section, and no units, limits,
  defaults, legal values or explanation of behaviour; those are written once,
  in the attribute's or command's entry on the node's reference-manual page.
  Add a second paragraph only for an implementation note the code cannot
  show. A `set_` method the model calls rather than the deck
  (`set_internal_bounds`) is no DSL setter and follows the Docstrings rules.
- A DSL setter's parameters are generic, as its name says what it sets: an
  attribute setter takes `value`, a command `key, value` or
  `key1, key2, value`. A local holding a converted key or value is named for
  what it holds (`energy_type`, `saving`).
- Deck-facing attribute names keep their DSL casing, Title case with acronyms
  as words (`Capex`, `LowerHeatingValue`), which `attribute_to_setter`
  (`navigate/util/naming.py`) splits at each capital into a setter name.
- Name the kinds a setter may be handed and store once, in
  `navigate/core/types_.py`, and use those aliases at every attribute
  definition and setter parameter. The alias matches the node types the
  setter passes as `type_=` to its `assign_*` call (`ScalarInput` for
  `type_=VARIABLE`). An attribute carries the storage kind (`*Input`); a
  setter parameter carries the matching argument kind (`*Argument`), which
  has `float` where the storage kind has `Scalar`, as the setter wraps it
  through `as_scalar`. `NumberInput` serves as both. An optional attribute
  still unset after construction is `<alias> | None`; never fold `None` into
  an alias, as `None` on a DSL input means unassigned.
- An attribute every deck must assign is marked `required=True` on its
  setter's `deck_attribute` decorator and declared in `__init__` by
  annotation alone (`self.start_date: np.datetime64`), with no value and no
  `None`. The parser checks it before anything reads it (`ARCHITECTURE.md`,
  Node lifecycle), so neither `check_requirements` nor any reader tests it
  again. An internal attribute that a fixed initialization step sets before
  any reader runs is declared the same way (`self.primary_fuel_type:
  FuelTypeID`). An attribute required only under a condition on other
  attributes stays `<alias> | None` and is tested in `check_requirements`.

## Dynamic state and results

- An expectation accessor takes its keys, outermost first, then the time
  step, the order a results field is indexed in; a setter or adder takes the
  value last: `set_bunker_wtt(fuel_name, emission_name, idx, wtt)` mirrors
  `get_bunker_wtt(fuel_name, emission_name, idx)`.
- An expectation getter reads either one key or the whole storage, never one
  or the other depending on its arguments. Its key parameter has no default,
  as a `None` default would spell that switch. The whole-storage read is a
  separate getter, named in the plural where the keyed getter is singular. A
  time index defaulting to the full slice is allowed.
- The results classes (`navigate/core/results/`) are dataclasses written and
  read as plain fields, sharing the run-wide timeline, fuel and emission
  constants and the conversions by them in `ResultsContext`. A time step
  writes a result in the quantity it computed (a mass, a ton of each
  emission, a price per ton), for `post_process` to convert and combine
  (`ARCHITECTURE.md`, Data-flow invariants); a field `post_process` writes
  raises `AttributeError` if read before. The `result(unit)` declarations are
  the code's only record of the results and their units.
- Read a calculator or a `Scalar` (`ARCHITECTURE.md`, Vocabulary) only
  through `.get`, which may take a variable number of inputs and may return a
  default or a pre-computed value.

## Typing

- Annotate a local variable only where mypy cannot infer its type, such as an
  empty container, a `None`-initialized accumulator, or a value from an
  untyped library.

## Docstrings

Ruff `D` with the numpy convention decides where a docstring is required and
its section layout; the rules below cover the content.

- A summary states what the function does, plus a why the code cannot show,
  and nothing more.
- A `Parameters` section is optional; once present it lists every argument
  (ruff `D417`), each named without its type (the signature carries it) and
  described in one line where one line fits (ruff `DOC102` checks the names
  against the signature).
- `Returns` takes the numpydoc shape: a type line, with the description
  indented under it. The type repeats the return annotation, as numpydoc
  requires a type for each return value.
- A module docstring states the purpose of the file, in one line where one
  line fits. A module defining a class used outside its package also says
  where the class is used.
- A class docstring states the responsibility of the class in one line.
  `__init__` never carries a docstring. A class callers instantiate directly
  (`Scalar`, the calculators) adds a `Parameters` section describing the
  constructor arguments. A class only the framework constructs stays at one
  line; this covers every node except the calculators, as a node's inputs are
  DSL attributes documented in the reference manual.
- A node's lifecycle methods and the methods of expectation classes need no
  docstring (ruff `D102` is waived for `nodes/`, `general_nodes/` and
  `expectations/` under `navigate/core/`, so a DSL setter's is unchecked).

## Comments

- Write a comment only for a why the code cannot show; by default write none.
- Never restate the code. Never frame a comment against a previous version or
  a rejected alternative; it reads correctly to someone who never saw another
  version.
- No reference to when or for which change code was written (a date, "added
  for the X flow").
- Start a comment with a lowercase letter, unless its first word is an
  identifier, acronym or proper noun spelled with a capital.
- Keep a short comment on one `#` line; wrap a longer one into a block of `#`
  lines that reads as one paragraph (ruff `E501` caps the line length).
- In an `if`/`elif` chain, a comment on why the branching exists goes above
  the `if`; a comment on one branch is the first line inside that branch.
- Write comments and docstrings in plain ASCII: `-` for a dash, `->` for an
  arrow, straight quotes. User-facing message strings (errors, log messages)
  and licence header lines are exempt (ruff flags only confusables such as
  `–` and `’`: `RUF002` in docstrings, `RUF003` in comments, `RUF001` in any
  string, an exempt one included).

## Layout

- Blank lines separate logical sections; statements forming one conceptual
  operation stay adjacent. In particular:
  - Exit early through a guard clause (a short `if` ending in `return`,
    `continue`, `break` or `raise`) instead of nesting the rest of the body,
    and follow the guard with a blank line (ruff `RET` flags an `else` after
    an exit).
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
- Test computed floats for equality within a named tolerance constant
  (`TOLERANCE` in `navigate/util/numeric.py`), through `abs`, `math.isclose`
  or `np.isclose`: `abs(power_to - power_from) > TOLERANCE`. Exact `==`/`!=`
  is allowed for a zero guard (skipping or masking an exact zero, or
  protecting a division) and against an assigned value (a default, a
  sentinel).

## Validation and dynamic access

- Validate deck input in the `assign_*` functions (`navigate/core/assign.py`)
  the setters call and in the `check_*` hooks. An error names the node, the
  attribute and the offending value; an `assign_*` error leaves the node and
  attribute to the parser. `calculate_*` and expectation methods contain no
  checks; past validation, trust the types (mypy `warn_unreachable` flags a
  check the types already rule out).
- In `navigate/`, confine dynamic attribute access (`hasattr`, `getattr`,
  `setattr`, `delattr`, `vars`, `__dict__`) to the boundary modules:
  `navigate/parser/` (DSL dispatch), `navigate/output/` (results by name) and
  `navigate/app/` (the `extra` keys of a log record). The exception is
  `navigate/core/dsl.py`, which uses `vars` to collect decorator marks from
  methods defined on a class and its bases.

## Logging

- A module logs through a module-level `logger = logging.getLogger(__name__)`
  and imports nothing from `navigate` to log, as `RunLog` alone configures
  logging (ruff `LOG` flags calls on the root logger).
- Pass a heading or a table through `extra` (`heading=True`, `table={column
  name: values}`) for `RunLog` to frame or render, never assembled into the
  message (ruff `G001` to `G004` flag a message formatted in the call).
