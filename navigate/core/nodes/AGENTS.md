<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Nodes

One module per DSL node type. The class is the keyword's runtime object, and
its `set_*` methods are the DSL surface: every attribute and command the parser
accepts maps to one by name (`navigate/util/naming.py`) and validates its input
through `navigate/core/assign.py`.

- Setter docstrings are the user's documentation of that attribute and carry
  an `Examples` block with valid deck values. Lifecycle methods (`initialize*`,
  `calculate_*`) carry none; the docstring check is waived here for that.
- Methods are ordered `__init__`, DSL setters, `initialize*`, `calculate_*`,
  getters.
- Class docstrings stay one line: a node's inputs are DSL attributes,
  documented in the reference manual.
- Deck-facing names keep their DSL casing (`TotalEquivalentWTT`); Python
  identifiers are snake_case with acronyms lowercased (`set_fuel_wtt`).
- A new attribute or command touches every place listed under "DSL surface"
  in `ARCHITECTURE.md`; nothing checks the manual page for you.
- `__init__.py` is empty on purpose: import a class from its own module.
