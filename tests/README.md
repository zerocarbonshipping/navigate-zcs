<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Test suites

Where a check belongs:

- Exact behavior of a function or class, with an expected value derivable
  independently of the implementation → `tests/unit` (conventions:
  `tests/unit/README.md`).
- Coverage of the DSL attribute/command surface → `tests/attribute`.
- Domain-expected behavior of a full simulation → `tests/guardrails`
  (conventions: `tests/guardrails/README.md`).
- "Shipped decks still parse and run" → `make test-tutorials` /
  `make test-examples` (exit-code smoke over the committed tutorial and
  example decks; never add assertions there).

`make test-all` chains every suite; per-suite targets are in the Makefile.
