<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Parser

Turns a deck (`.nav` with `DEFINE` and `EVENTS`, plus `.inc` includes) into
nodes, then drives the clock: `EVENTS` is a date-keyed queue of assignments
that the simulation replays step by step, so the parser owns the timeline.
Nodes a deck references but never declares, and modules it `Load`s, resolve
from the assumptions root, `user/` before `installation/`.

- `grammar.lark` is generic and small. What a node may say lives in the tables
  `_keywords.py`, `_attributes.py` and `_commands.py`, keyed by the type
  constants in `navigate/core/node_type.py`. A new attribute or command changes
  the tables, not the grammar.
- Deck values arrive untyped. Validating them and deriving values from them is
  the node setters' job, not this package's and not the calculation code's,
  which trusts what it receives.
- This is the boundary where `hasattr`/`getattr` dispatch on DSL names is
  legitimate.
- Errors raised here carry the deck location (file, include, line) so the
  user can find the offending statement; keep that when adding one.
