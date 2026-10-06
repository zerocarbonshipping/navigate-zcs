<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a documentation pull request

- **What changed** says what was wrong or missing, and the source of truth
  each correction was checked against: the setter and its docstring, the
  parser table, or the code path.
- Errors in the reference manual get a changelog entry like bugs
  (`CONTRIBUTING.md`, Changelog). Other documentation changes get none; say
  so.
- The reference manual describes behaviour as users see it, with no
  modelling derivations. Internals go in the root files and the folder
  READMEs.
- The docs build runs in CI, so Verification does not report it. When
  nothing else was checked, Verification says so in one line.
