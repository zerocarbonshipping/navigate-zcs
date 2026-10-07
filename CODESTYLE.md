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

- Give parameters, variables and attributes descriptive names, not single
  letters or opaque prefixes: `multipliers_total`, not `y`. The index
  variable of a loop or comprehension (`i`, `j`, `k`, `t`) is exempt.
- Use domain words, not abbreviations: `newbuild_technology`, not `nb_tech`.
  Abbreviate only an established domain term (`co2`, `lng`, `capex`).
- Name what a value means, not its container: `pending_orders`, not
  `order_list`. No generic suffixes (`_data`, `_obj`, `_thing`).
- Phrase boolean names positively: `is_ready`, not `is_not_ready`.
- Reserve ALL_CAPS for enum members (`AMMONIA`, `FLAT`) and module-level
  constants (ruff `N806` flags it on function locals).
- Prefix a name with an underscore when it is used only within its scope: a
  module used only within its package, a class or function used only within
  its module, an attribute or method used only within its class. A name used
  outside its scope carries no underscore (ruff `SLF001` flags access to an
  underscored attribute from outside its class).
- Keep an external API's casing only where it is called, and bind the result
  to a snake_case name: `change_coefficient = model.chgCoeff`.
- If a function can only be named with "and", split it.

## Classes and attributes

- Define every instance attribute in `__init__` and annotate it there, never
  on the class body. Dataclass fields, enum members and `ClassVar` constants
  are the exceptions.
- An attribute definition carries no trailing comment. What there is to say
  about one attribute is either a why (see Comments) or belongs in the class
  docstring. A group comment heading a run of attributes stays. An enum member
  carries exactly one trailing comment, stating what it stands for.
- Read and write attributes directly. Add a getter or setter only for a need a
  plain attribute cannot meet; the sanctioned ones are the DSL setters, the
  expectation and profile accessors, and the calculators' `.get`.
- Prepopulate a dictionary with its full key set wherever the set is known up
  front, so a missing key fails loudly instead of growing the dictionary. A
  dictionary keyed by nodes or enum members is always prepopulated at
  initialization: every node is known after parsing, and the enum types in
  `navigate/core/enum_.py` are fixed.

## Nodes and the DSL

- Every attribute a deck can assign on a node has a DSL setter
  (`set_propulsion_load` on `Vessel`), sits in the node's `# external
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
- The lifecycle hooks a node overrides (`check_requirements`,
  `apply_defaults`, `initialize_dependencies`, `apply_command_defaults`,
  `check_consistency`, `check_dynamic_consistency`, `initialize_expectation`,
  `initialize_profile`, `calculate_expectation`, `calculate_profile`) carry no
  docstring; ruff `D102` is waived for `navigate/core/nodes/` and
  `navigate/core/general_nodes/` to allow it.
- Deck-facing attribute tokens keep their DSL casing (`CAPEX`,
  `TotalEquivalentWTT`); `attribute_to_setter` (`navigate/util/naming.py`)
  maps them to setter names.
- Order a node class's methods: `__init__`, DSL setters, the lifecycle hooks
  in the order the parser runs them, `calculate_*`, getters last.
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

- Pass a dynamic result from one module to another through `node.expectation`
  or `node.profile`, never through a plain node attribute.
- The expectation classes (`navigate/core/expectations/`) and profile classes
  (`navigate/core/profiles/`) are accessed through getters, adders and
  setters, which keep dynamic state and output apart from user input and
  temporary results. Their methods carry no docstring; ruff `D102` is waived
  for both packages.
- A profile getter takes no parameters and returns the whole timeline array
  or the whole dictionary; the caller indexes the result.
- An expectation getter reads either one key or the whole storage, never one
  or the other depending on its arguments. Its key parameter has no default,
  as a `None` default would spell that switch. The whole-storage read is a
  separate getter, named in the plural where the keyed getter is singular. A
  time index defaulting to the full slice is allowed.
- Read the calculators (`Curve`, `Forecast`, `Surface`, `Timetable`,
  `Variable`) and the `Scalar` wrapper through `.get`, which may take a
  variable number of inputs and may return a default or a pre-computed value.

## Typing

- Annotate a local variable only where mypy cannot infer its type: an empty
  container or a `None`-initialized accumulator.

## Docstrings

Ruff `D` with the numpy convention decides where a docstring is required and
its section layout; the rules below cover the content.

- A summary states what the function does, plus a why the code cannot show,
  and nothing more.
- `Parameters` names each argument without its type (the signature carries
  it) and describes it in one line where one line fits (ruff `D417` and
  `DOC102` check the names against the signature).
- `Returns` takes the numpydoc shape: a type line, with the description
  indented under it. The type repeats the return annotation, as numpydoc
  requires a type for each return value.
- A module docstring states the purpose of the file, in one line where one
  line fits. A module defining a class used across the codebase also says
  where the class is used.
- A class docstring states the responsibility of the class in one line.
  `__init__` never carries a docstring. A class callers instantiate directly
  (`Scalar`, the calculators) adds a `Parameters` section describing the
  constructor arguments. A class only the framework constructs stays at one
  line; this covers every node, whose inputs are DSL attributes documented in
  the reference manual.

## Comments

- Write a comment only for a why the code cannot show; by default write none.
- Never restate the code. Never frame a comment against a previous version or
  a rejected alternative; it reads correctly to someone who never saw another
  version.
- No dated or relative references ("added for the X flow").
- Start a comment with a lowercase letter, unless its first word is an
  identifier, acronym or proper noun spelled with a capital.
- Keep a short comment on one `#` line; wrap a longer one into a block of `#`
  lines that reads as one paragraph (ruff `E501` caps the line length).
- In an `if`/`elif` chain, a comment on why the branching exists goes above
  the `if`; a comment on one branch is the first line inside that branch.

## Layout

- Blank lines separate logical sections; statements forming one conceptual
  operation stay adjacent. In particular:
  - Exit early through a guard clause (a short `if` ending in `return`,
    `continue`, `break` or `raise`) instead of nesting the rest of the body,
    and follow the guard with a blank line (ruff `RET` flags an `else` after
    an exit).
  - Logging and other string-assembly statements form their own section, with
    a blank line above and below.
  - The end of a block is no section break by itself: a short block that
    belongs to the operation around it, such as a lookup loop or an
    `if`/`else` choosing one value, is followed directly by the next
    statement. After a block that carries out a step of its own, a blank line
    starts the next section.
- Group related local variables; do not interleave them with logic.
- Write comments and docstrings in plain ASCII: `-` for a dash, `->` for an
  arrow, straight quotes. User-facing message strings (errors, log messages)
  and licence header lines are exempt.

## Numerics

- State a physical quantity's unit in the docstring of the parameter, return
  value or class attribute it applies to, written "<description>, in
  <unit>.": `Fuel price, in USD/GJ.`
- Compare computed floats with `math.isclose`, `np.isclose` or `np.allclose`
  and a named module-level tolerance constant, such as `TOLERANCE` in
  `navigate/util/numeric.py`. Use exact `==` or `!=` on a float only as a zero
  guard before a division, or against a value that was assigned rather than
  computed (a default, a sentinel).

## Validation and dynamic access

- Validate at the input boundary and raise domain-specific errors carrying the
  offending input's context. Past the boundary, trust the types: no defensive
  re-validation inside calculation code.
- Confine dynamic attribute access (`hasattr`, `getattr`, `setattr`) to the
  boundary modules: `navigate/parser/` (DSL dispatch), `navigate/output/` and
  `navigate/app/` (the `extra` keys of a log record). Elsewhere it marks a
  design problem to fix.

## Logging

- A module logs through a module-level `logger = logging.getLogger(__name__)`
  and imports nothing from `navigate` to log (ruff `LOG` flags calls on the
  root logger).
- Pass a heading or a table through `extra` (`heading=True`, `table={column
  name: values}`), never assembled into the message.
