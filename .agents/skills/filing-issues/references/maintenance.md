<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a maintenance issue

- **Description** states the debt and what it costs: what is harder to read,
  change or test because of it (#415).
- **Location** lists every site. For a pattern spread over many files, give
  the grep that finds them all.
- **Proposed resolution** describes the end state, not the steps to it.
- **A "Decide whether…" issue** is for a choice that has to be made first.
  Its resolution lays out each option and what it would entail (#426).
- A refactor may change log, console or report output where that makes the
  code simpler or clearer. Name any such change; the pull request states it
  as a user-visible effect and gives it a CHANGELOG entry.
- **Verification** may give a grep whose result shows the end state was
  reached (#426).
