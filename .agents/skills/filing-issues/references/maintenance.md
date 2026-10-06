<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a maintenance issue

Maintenance covers refactoring, tests, typing and tooling debt: changes that
leave behaviour as it is.

- **Description** states the debt and what it costs: what is harder to read,
  change or test because of it (#415).
- **Location** lists every site. For a pattern spread over many files, give
  the grep that finds them all.
- **Proposed resolution** describes the end state, not the steps to it.
- **A "Decide whether…" issue** is for a choice that has to be made first.
  Its resolution lays out each option and what it would entail (#426).
- **Verification** says how a fix would show behaviour neutrality beyond
  what CI runs:
  - byte-identical report output for the affected decks, base versus
    branch, since the regression suite has a noise floor and is not a proof
    (`tests/regression/README.md`);
  - or "nothing under `navigate/` changes";
  - or a grep whose result shows the end state was reached (#426).
- Verification names no suites to run; CI runs them.
