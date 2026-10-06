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
- **Verification** names the affected decks: every deck under
  `simulations/examples/` and `tutorials/` whose run reaches the changed
  code. It says how to show that what the model computes is unchanged, base
  versus branch, by the standard in `CONTRIBUTING.md`, Evidence in a pull
  request.
- A refactor may change log, console or report output where that makes the
  code simpler or clearer. Name any such change; the pull request states it
  as a user-visible effect and gives it a CHANGELOG entry.
- A grep whose result shows the end state was reached may serve as well
  (#426). A run CI does not do, such as a reference scenario under
  `simulations/scenarios/`, is named with what it should show.
