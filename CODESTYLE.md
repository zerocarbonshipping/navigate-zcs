<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Code Style

This document holds the conventions that ruff (`.ruff.toml`) and mypy
(`mypy.ini`) do not check; `ruff format` owns the layout within statements.
Where a tool checks part of a rule, a parenthetical names the check. Where
this document and the configuration disagree, the configuration is the
arbiter.

## Naming

- Name functions, methods, variables and attributes in snake_case with
  acronyms lowercased: `set_fuel_wtt`, `self.fuel_wtt` (ruff `N` checks every
  name except an attribute assigned on an object).
- Give parameters, variables and attributes descriptive names, not single
  letters or opaque prefixes: `multipliers_total`, not `m`. Exempt are an
  integer index of a loop or comprehension (`i`, `j`, `k`, `t`), but not an
  element or key variable, and the axis variables `x`, `y` of a table or
  interpolation.
- Use domain words, not abbreviations: `newbuild_technology`, not `nb_tech`.
  Abbreviate only a term the DSL or the reference manual uses (`co2`, `lng`,
  `capex`, `wtt`).
- Name what a value means, not its container: `pending_orders`, not
  `order_list`. No generic suffixes (`_data`, `_obj`, `_thing`).
- Phrase boolean names positively: `is_ready`, not `is_not_ready`.
- Reserve ALL_CAPS for enum members (`AMMONIA`, `FLAT`), module-level
  constants and `ClassVar` constants (ruff `N806` flags it on function
  locals).
- An underscored name is never used outside its scope: a module outside its
  package, a class or function outside its module (outside its package when
  the module is underscored too), an attribute or method outside its class.
  Use from `tests/` does not count (ruff `SLF001` flags `obj._name` on any
  object but `self`, `cls` or an instance of the enclosing class).
- Keep an external API's casing only where it is called, and bind the result
  to a snake_case name: `change_coefficient = model.chgCoeff`. The solver
  shims (`navigate/simulation/bunker/solver.py`, `solver_highs.py`) mirror
  gurobipy's names (ruff `N802` is waived there).
- If a function can only be named with "and", split it.

## Classes and attributes

- Define every instance attribute in `__init__` and annotate it there, never
  on the class body. Dataclass and `NamedTuple` fields, `Protocol` members,
  enum members and `ClassVar` constants are the exceptions.
- An attribute definition carries no trailing comment. What there is to say
  about one attribute is either a why (see Comments) or belongs in the class
  docstring. A group comment heading a run of attributes is allowed. An enum
  member carries exactly one trailing comment, stating what it stands for.
- Read and write attributes directly. Do not add a method that only returns
  or assigns an attribute, except the DSL setters, the expectation and profile
  accessors, and `.get`.
- Prepopulate a dictionary with its full key set wherever the set is known up
  front, so a missing key fails loudly instead of growing the dictionary. A
  dictionary keyed by nodes or enum members is always prepopulated at
  initialization: every node is known after parsing, and the enum types in
  `navigate/core/enum_.py` are fixed.

## Nodes and the DSL

- Every attribute a deck can assign on a node or general node has a DSL
  setter (`set_propulsion_load` on `Vessel`), sits in the node's `# external
  variables` group and has an entry on the node's reference-manual page. The
  `# internal variables` group holds what the model sets; none of it has a
  DSL setter.
- A DSL setter carries a docstring written for developers: one line naming
  what the setter stores, e.g. `"""Set the volumetric size of the tank."""`.
  It has no `Parameters` or `Examples` section, and no units, limits,
  defaults, legal values or explanation of behaviour; those are written once,
  in the attribute's or command's entry on the node's reference-manual page.
  Add a second paragraph only for an implementation note the code cannot
  show. A `set_` method the model calls rather than the deck
  (`set_internal_bounds`) is no DSL setter and follows the Docstrings rules.
- Deck-facing attribute tokens keep their DSL casing (`CAPEX`,
  `TotalEquivalentWTT`); `attribute_to_setter` (`navigate/util/naming.py`)
  maps them to setter names.
- Order a node class's methods: `__init__`; DSL setters; the lifecycle hooks
  it overrides, in the order `check_requirements`, `apply_defaults`,
  `apply_command_defaults`, `check_consistency`, `initialize_dependencies`,
  `initialize_expectation`, `initialize_profile`, `check_dynamic_consistency`,
  `calculate_expectation`, `calculate_profile`; other `calculate_*` methods;
  getters last.
- Name the kinds a setter may be handed and store once, in
  `navigate/core/types_.py`, and use those aliases at every attribute
  definition and setter parameter. The alias matches the setter's `type_=`
  argument. An attribute carries the storage kind (`*Input`); a setter
  parameter carries the matching argument kind (`*Argument`), which has
  `float` where the storage kind has `Scalar`, as the setter wraps it through
  `as_scalar`. `NumberInput` serves as both. An optional attribute still unset
  after construction is `<alias> | None`; never fold `None` into an alias.
- An attribute every deck must assign is listed in `NODE_REQUIRED_ATTRIBUTES`
  or `GENERAL_NODE_REQUIRED_ATTRIBUTES` (`navigate/parser/_attributes.py`) and
  declared in `__init__` by annotation alone (`self.start_date:
  np.datetime64`), with no value and no `None`. The parser guarantees it is
  set before any node reads it, so neither `check_requirements` nor any reader
  tests it again. An internal attribute that a fixed initialization step sets
  before any reader runs is declared the same way (`self.primary_fuel_type:
  FuelTypeID`). An attribute required only under a condition on other
  attributes stays `<alias> | None` and is tested in `check_requirements`.

## Dynamic state and results

- A value computed during the time loop and read by another module lives on
  `node.expectation` or `node.profile`, not on a plain node attribute.
- The expectation classes (`navigate/core/expectations/`) and profile classes
  (`navigate/core/profiles/`) are accessed through getters, adders and
  setters, which keep dynamic state and output apart from user input and
  temporary results.
- A profile getter takes no parameters and returns the whole timeline array
  or the whole dictionary; the caller indexes the result.
- An expectation getter reads either one key or the whole storage, never one
  or the other depending on its arguments. Its key parameter has no default,
  as a `None` default would spell that switch. The whole-storage read is a
  separate getter, named in the plural where the keyed getter is singular. A
  time index defaulting to the full slice is allowed.
- Read the calculators (`Curve`, `Forecast`, `Surface`, `Timetable`,
  `Variable`) and the `Scalar` wrapper only through `.get`, which may take a
  variable number of inputs and may return a default or a pre-computed value.

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
- A node's lifecycle hook overrides and the methods of expectation and profile
  classes need no docstring (ruff `D102` is waived for `nodes/`,
  `general_nodes/`, `expectations/` and `profiles/` under `navigate/core/`).

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
  arrow, straight quotes (ruff `RUF002`/`RUF003` flag confusables such as `–`
  and `’`; the rest is unchecked). User-facing message strings (errors, log
  messages) and licence header lines are exempt.

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
  (`TOLERANCE` in `navigate/util/numeric.py`): `math.isclose(a, b,
  abs_tol=TOLERANCE)`, `np.isclose(a, b, atol=TOLERANCE)`, or `abs(x) <
  TOLERANCE` for zero. Exact `==`/`!=` is allowed for a zero guard (skipping or
  masking an exact zero, or protecting a division) and against an assigned
  value (a default, a sentinel).

## Validation and dynamic access

- Validate deck input in the `assign_*` functions (`navigate/core/assign.py`)
  the setters call and in the `check_*` hooks. An error names the node, the
  attribute and the offending value; an `assign_*` error leaves the node and
  attribute to the parser. `calculate_*` and expectation methods contain no
  checks; past validation, trust the types (mypy `warn_unreachable` flags a
  check the types already rule out).
- In `navigate/`, confine dynamic attribute access (`hasattr`, `getattr`,
  `setattr`) to the boundary modules: `navigate/parser/` (DSL dispatch),
  `navigate/output/` (report getters) and `navigate/app/` (the `extra` keys of
  a log record).

## Logging

- A module logs through a module-level `logger = logging.getLogger(__name__)`
  and imports nothing from `navigate` to log (ruff `LOG` flags calls on the
  root logger).
- Pass a heading or a table through `extra` (`heading=True`, `table={column
  name: values}`), never assembled into the message.
