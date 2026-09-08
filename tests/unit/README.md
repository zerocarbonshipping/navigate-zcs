<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Unit tests

Fast, isolated tests of a single function or class. For which suite a check
belongs to, see `tests/README.md`.

## What earns a unit test

All three must hold. A test that fails any of them is deleted in the same
pull request that touches its area — the suite's value is the precision of
its signal, not its size.

1. **Independent oracle.** The expected value is derivable without running
   the code: hand math, the DSL reference, a documented contract. A value
   copied from current output turns the test into a regression pin that
   condemns every legitimate change; regression pinning is a golden-baseline
   suite's job, not this one's.
2. **Right altitude.** The test targets the narrowest module that owns the
   logic — a shared base or pure kernel (interpolation in `_Table1D`, not in
   each calculator node built on it). Subclasses and callers are tested only
   for their own delta.
3. **It pins a breakable decision.** Validation, math, boundary and edge
   handling — behavior a future change could plausibly and silently get
   wrong. Never construction or field assignment, `__repr__`, `isinstance`,
   or pass-through delegation.

## Style

- A table of (input, expected) pairs is one parametrized test, not one
  function per pair.
- Build real nodes (`set_*` + `initialize()`) instead of mocking them —
  `tests/unit/fleet/test_residual_energy.py` is the pattern. A test that
  needs screens of mock setup is testing at the wrong altitude.
- Importing a shared private base or kernel that solely owns the logic is
  correct; importing private steps of a public function pins its
  decomposition — test the public function instead.
- Numeric tolerances are module-level constants whose rationale lives in a
  comment on the constant (same convention as the guardrail suite).

## Refactoring

A behavior-preserving refactor adds no tests. If it forces test rewrites
beyond import paths, the tests sit at the wrong altitude: move them up to
the surviving surface in the same pull request — never duplicate them onto
the new shape.
