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
  code. For one that writes no report, the evidence is every node's profile
  and expectation, pickled after a full run on base and on branch, and
  compared. The regression suite is no substitute: its baselines cover few
  decks and carry a noise floor (`tests/regression/README.md`).
- A grep whose result shows the end state was reached may serve as well
  (#426). A run CI does not do, such as a reference scenario under
  `simulations/scenarios/`, is named with what it should show.
