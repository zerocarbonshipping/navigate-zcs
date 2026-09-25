<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Code Style

This document carries the conventions the tooling cannot check. Everything
mechanical lives in the lint and type-check configuration (`.ruff.toml` and
`mypy.ini`); formatting and layout within statements are owned by `ruff format`
and are not discussed here. The configuration is the arbiter: files listed in
its generated ratchet regions predate the tooling — clean them whole-file in
style-only commits, and never add new entries.

## Naming

- Prefer descriptive names. A single-letter parameter or opaque prefix forces
  every reader to chase its definition. If a value is "the sum of multipliers",
  call it `multipliers_total`, not `y`.
- Prefer domain names over abbreviations: `newbuild_technology`, not `nb_tech`.
  Abbreviations are acceptable only as established domain terms (`co2`, `lng`).
- Prefer names that reveal intent (`pending_orders`) over names that describe
  shape (`order_list`); avoid generic suffixes (`_data`, `_obj`, `_thing`).
- Boolean names read positively (`is_ready`, not `not_unready`).
- The underscore prefix marks internals: files used only within their package,
  classes and functions used only within their file, attributes used only
  within their class. What counts as internal is a judgment call; the linter
  only polices access from outside.
- A value taken from an external API keeps the foreign casing at the call site
  (`change_coefficient = model.chgCoeff`).

## Classes and attributes

- Attributes are defined in `__init__` only, never on the class body, and are
  annotated there. Dataclass fields, enum members, and `ClassVar` constants are
  the exceptions.
- An attribute definition carries the annotation alone and no trailing
  comment; a group comment heading a run of attributes stays. Anything worth
  saying about one attribute is either a why, under the Comments section, or
  belongs in the class docstring.
- Access attributes directly; do not add getters or setters without a need a
  plain attribute cannot express. Sanctioned exceptions are listed in the
  repository-specific section below.
- Prefer dictionaries prepopulated with their full key set over keys added on
  the fly: when the key set is known up front, a missing key should fail
  loudly, not grow the dictionary.

## Typing

- Annotate every `__init__` attribute.
- Do not annotate local variables unless the type checker cannot infer them
  (empty containers, `None`-initialized accumulators).

## Docstrings

Where docstrings are required is enforced by the linter; their content is
judgment:

- Summaries are terse: what the function does, plus any non-obvious why.
  Verbose docstrings are explicitly discouraged.
- `Parameters` gives each argument one line, without types (the signature has
  them).
- `Returns` follows the numpydoc shape: a type line with the description
  indented under it. Here the type deliberately duplicates the annotation -
  the documentation renderer reads the docstring alone, and a bare
  description in the type position renders wrong.
- State the unit wherever a parameter or return value has one.
- Module docstrings are one line where one line fits, stating the purpose of
  the file; a module defining a class used across the codebase also says
  where the class is used.
- Class docstrings state the responsibility of the class in one line. A class
  that callers instantiate directly extends it with a `Parameters` section
  describing the constructor arguments (`__init__` itself never carries a
  docstring); a class constructed only by the framework stays at one line.

## Comments

- Default to none; comment only a why the code cannot show.
- Never restate the code, and never frame a comment against a previous version
  or a rejected alternative - it must read correctly to a reader who never saw
  any other version.
- No dated or relative references ("added for the X flow") - they rot.
- Comments start lowercase and use plain ASCII punctuation.
- Short comments stay on one `#` line; longer ones wrap into a block within the
  line-length budget so they read as a paragraph:

```python
# adjust the rate so downstream consumers see a stable signal even when the
# upstream source briefly drops out; passing zeros instead would leak into
# the moving average and produce visible artefacts.
rate = smooth(rate)
```

- In an `if`/`elif` chain, a comment explaining why the branching exists goes
  above the `if`; a comment explaining one branch goes as the first line
  inside that branch.

## Layout beyond the formatter

The formatter owns spacing within statements; blank lines are yours:

- Blank lines separate logical sections; statements forming one conceptual
  operation stay adjacent.
- Keep simple control flow compact - no blank line merely because a construct
  ended; place one after a non-trivial construct before the next section.
- Prefer guard clauses over nesting, and follow a guard (a short `if` ending
  in `return`/`continue`/`break`/`raise`) with a blank line so the structural
  break stays visible.
- Logging and other string-assembly statements form their own visual section,
  with a blank line above and below.
- Group related local variables; do not interleave them with logic.
- If a function can only be named with "and", split it.

## Input validation and dynamic access

- Validate at the input boundary and raise domain-specific errors carrying the
  offending input's context. Past the boundary, trust the types: no defensive
  re-validation inside calculation code.
- Dynamic attribute access (`hasattr`/`getattr`/`setattr`) belongs to the
  boundary modules enumerated in the repository-specific section; elsewhere it
  signals a design problem to fix, not to suppress.

## Navigate-specific conventions

### Nodes and the DSL

- Any variable on a `Node` or `_GeneralNode` subclass exposed via the DSL needs
  a setter (e.g. `set_propulsion_load` on the `Vessel` node).
- DSL setters are public-facing API and always carry a docstring; the node
  lifecycle methods (`initialize`, `reinitialize`, `check_requirements`,
  `apply_defaults`, `apply_command_defaults`, `check_consistency`,
  `initialize_dependencies`, `calculate_expectation`, `calculate_profile`)
  need none — the docstring check is waived for `navigate/core/nodes/` to
  allow this.
- All Python identifiers, including DSL command names, are pure snake_case
  with acronyms lowercased (`set_fuel_wtt`, `capex`). Deck-facing attribute
  tokens keep their DSL casing (`CAPEX`, `TotalEquivalentWTT`) and are mapped
  to method names by `attribute_to_setter` (`navigate/util/naming.py`).
  ALL_CAPS is reserved for enum keyword values (`AMMONIA`, `FLAT`) and
  module-level constants.
- Node classes order their methods: `__init__`, DSL setters, the lifecycle
  hooks in the order the parser runs them, `calculate_*`, getters last.
- Nodes are parser-constructed, so node class docstrings stay one line (their
  inputs are DSL attributes, documented in the DSL reference). The
  caller-instantiated classes - `Scalar` and the calculators - document
  constructor parameters in the class docstring per the shared rule.
- Every attribute in a node `__init__` has a DSL setter whose docstring is
  what its reference-manual page is written from, so anything said about the
  attribute is said there.
- The kinds a setter may store are named once, in
  `navigate/core/nodes/input_kinds.py`, and used at every attribute
  definition. The alias matches the setter's `type_=` argument, and an
  attribute still unset after construction spells it `<alias> | None` rather
  than folding `None` into an alias. Setter parameters are annotated
  `float | <alias>`, the unwrapped value the parser passes, while the
  attributes carry the alias (`NumberInput`, stored unwrapped, is both).
- An attribute every deck must assign is listed as required in
  `navigate/parser/_attributes.py` and declared in `__init__` by annotation
  alone (`self.start_date: np.datetime64`), with no value and no `None`.
  The parser guarantees it is set before any node reads it, so neither
  `check_requirements` nor any reader tests it again. An attribute required
  only under a condition on other attributes stays `<alias> | None` and is
  tested in `check_requirements`.

### Dynamic state and results

- Dynamic cross-module results go through `node.expectation` / `node.profile`,
  never through plain attributes.
- The expectation classes (`navigate/core/expectations/`) and profile classes
  (`navigate/core/profiles/`) use getters/adders/setters deliberately: the
  indirection separates dynamic state and output from user input and temporary
  results.
- Profile getters take no parameters and return the whole timeline array or
  the whole dict; callers index the result. The signature is enforced by
  `tests/unit/core/test_profile_getters.py`.
- Expectation getters never switch between reading one key and reading the
  whole storage: a key is mandatory, and a whole-storage read is a separate
  getter, taking the plural name where a keyed getter holds the singular. A
  `None` default is what spells the switch, and
  `tests/unit/core/test_expectation_getters.py` rejects it.
- Calculator classes (`Curve`, `Forecast`, `Surface`, `Timetable`, `Variable`)
  and wrappers (`Scalar`) are read through `.get`, which may take a variable
  number of inputs and can return defaults or pre-computed values.

### Boundary modules

- Dynamic attribute access (`hasattr`/`getattr`/`setattr`) is confined to
  `navigate/parser/` (DSL dispatch) and `navigate/output/`.
- Dictionaries keyed by nodes or enum members are prepopulated at
  initialization: all nodes are known after parsing, and the enum types in
  `navigate/core/enum_.py` are fixed.
