<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a maintenance issue

- **Description** states the debt and what it costs: what is harder to read,
  change or test because of it.
- **Intended state** is the property the code should have once the debt is
  dealt with, never the steps or the mechanism to reach it.
- **Location** lists every site. For a pattern spread over many files, give
  the grep that finds them all.
- **A "Decide whether…" issue** is for a choice that has to be made first.
  It states the decision to be made and why it matters. Options already
  known may be listed under Considerations, with no recommendation.
- A refactor may change log, console or report output where that makes the
  code simpler or clearer; the pull request states any such change as a
  user-visible effect and gives it a CHANGELOG entry. An output change the
  intended state itself requires is named in the issue.
