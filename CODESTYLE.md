<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Code Style

This document describes the coding conventions for Navigate. It builds on the
`flake8` configuration (pep8) with the additional preferences below. When in
doubt, match the conventions of the file you are editing.

## General Guidelines

- Question the use of `isinstance()` in core modules. Type checking should be performed at the input level, and not redundant checks are needed later.
- Pre-define dicts instead of creating them on the fly, unless this comes with noticeable disadvantages.
- Local consistency wins. If a file already follows a different convention, match the file rather than imposing a global rule.

## Class variables

- A member variable accessed publicly is stored without a `_` prefix; one used only internally on the class keeps the `_` prefix (e.g. `initial_age_distribution` on the `_AssetManager` superclass node).
- Any variable on a `Node` or `_GeneralNode` subclass exposed via the DSL needs a setter (e.g. `set_propulsion_load` on the `Vessel` node).
- We do not use getters internally — public variables are accessed directly as plain attributes (`vessel.propulsion_load`).
- Member variables are always defined inside `__init__`, never on the class body itself.

## Typing

Type hints are required for all functions and classes, but **only on signatures and on class attributes inside `__init__`** — not on local variables inside method or function bodies.

```python
class Boat(Node):

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.price: int = 0
        self.length: float = 0.

    def add_bowsprit(self, length: float) -> float:
        total = self.length + length   # no inline annotation
        self.length = total
        return total
```

If type hints require importing that can cause circular references then import annotations and type checking.

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.module.file import Class
```

## Docstrings

Use the numpydoc shape shown below. Keep the summary terse — describe *what* the function does and any non-obvious *why*. Always include a `Parameters` section describing every argument; one short line per parameter is enough so a reader does not have to chase definitions.

Verbose docstrings are explicitly discouraged.

```python
def add_bowsprit(self, length: float) -> float:
    """
    Adds a bowsprit to the vessel, extending its length.

    Parameters
    ----------
    length
        Length of the bowsprit in meters.

    Returns
    -------
    New total length of the vessel.
    """

    self.length += length
    return self.length
```

## Layout and control flow

- A two-line `if` that ends in `continue` / `return` / `break` / `raise` is a guard. Always follow it with a blank line before the next logical step, so the structural break is visible.

```python
for item in items:
    if item.skip:
        continue

    if item.value < threshold:
        continue

    process(item)
```

- Treat **logging calls and other string-assembly statements** (`logger.*`, `warnings.warn`, multi-line message construction) as their own visual section. Surround them with a blank line above and below so they read as commentary on the surrounding logic, not as part of it.

```python
ratio = numerator / denominator

# potential comment related to the logging
logger.info("ratio for %s: %.4f", name, ratio)

for entry in entries:
    entry.value *= ratio
```

- Prefer guard clauses over deeply nested `if`/`else`.
- Group related local variables; do not interleave them with logic.
- Keep functions focused. If you cannot name what a function does without "and", consider splitting.

## Methods
If the lengths of a method name including arguments is too long it should be split over several lines.
This will typically be if the number of arguments is >3 but can depend on the length of the method name and arguments themselves.
Multiline method definitions should follow this format:

```python
method_name_with_many_arguments(argument1: Type,
                                argument2: Type,
                                argument3: Type,
                                argument4: Type,
                                argument5: Type
                                ) -> Type
```

## Containers
Smaller containers with short variable names can be defined on a single line
```python
t = (a, b, c)
d = {'a': x, 'b': y, 'c': z}
```

Longer containers should be defined over multiple lines with open and closing brackets on separate lines. For key, value pair containers, the containers should be column aligned
```python
t = (
  a_long,
  b_long, 
  c_long
)

d = {
  'a_long': x_long,
  'b_long': y_long,
  'c_long': z_long
}
```


## Naming

- Prefer descriptive names. A single-letter parameter or opaque prefix forces every reader to chase its definition; spell it out instead. If a value is "the sum of multipliers", call it `multipliers_total`, not `y`.
- Prefer clear domain names over abbreviations: `newbuild_technology`, not `nb_tech`. Abbreviations are acceptable only when they are the established domain term (`co2`, `lng`).
- Prefer names that reveal intent (`pending_orders`) over names that describe shape (`order_list`).
- Avoid generic suffixes like `_data`, `_obj`, `_thing`.
- Boolean names should read positively (`is_ready`, not `not_unready`).
- All Python identifiers, including DSL command names (node methods callable from `.nav`/`.inc` files), are pure snake_case; acronyms are lowercased (`set_fuel_wtt`, `capex`, not `set_fuel_WTT`, `CAPEX`). Deck-facing attribute tokens keep their DSL casing (`CAPEX`, `TotalEquivalentWTT`) and are mapped to the snake_case method names by `attribute_to_setter`. ALL_CAPS is reserved for enum keyword values (`AMMONIA`, `WTT`, `FLAT`) and module-level constants.
- Methods should be prefixed with `_` if they are internal and only used within the same file, e.g., `_internal_method`.
- Classes should be prefixed with `_` if they are internal and only used within the package where they are defined, e.g., `_InternalClass`.
- Files should be prefixed with `_` if they are internal and only used within the package where they are defined, e.g., `_internal_file.py`.

## Comments

- Default to no comment. Add one only when the *why* is not obvious.
- Never restate what the code already says.
- Do not leave dated or relative references in comments ("added for the X flow", "see the new feature") — they rot.
- Comments start with a lowercase letter, like ordinary running prose.
- Stick to plain ASCII punctuation. Avoid decorative characters like arrows (`→`, `=>`), bullets, or box-drawing.
- Short comments stay on a single `#` line. Longer comments are formatted as a multi-line block with a constrained width (match the surrounding line-length budget) so they read as paragraphs, not as one runaway line.

```python
# adjust the rate so downstream consumers see a stable signal even when the
# upstream source briefly drops out; the alternative — passing zeros — leaks
# into the moving average and produces visible artefacts.
rate = smooth(rate)
```

- For an `if` / `elif` / `else` chain:
  - If the *existence* of the branching needs explanation, put the comment **above** the `if`.
  - If each *branch* needs its own explanation, put the comment as the **first line inside** that branch.

```python
# legacy entries are stored under a different key, so dispatch up front.
if entry.is_legacy:
    # legacy path keeps the original ordering for downstream diff tooling.
    handle_legacy(entry)
elif entry.is_partial:
    # partial entries arrive without a checksum and must be verified inline.
    handle_partial(entry)
else:
    handle_full(entry)
```

Files should contain a block comment header explaining the purpose of the file.
For files where nodes are defined (e.g., `converter.py`) the header should include a description of where the
node can be assigned. E.g., the `Port` node is assigned both on the `Route` node through the `Ports` attribute 
and the `Regulation` node through the `Jurisdiction` attribute. Some nodes are not assigned anywhere, e.g., 
the `Fleet` node, in which case that should be mentioned.

```python
"""
This is a block comment.
"""

import ...
```