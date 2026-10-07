<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a performance pull request

- **Opening paragraph:** the improvement, with its scale, as a speed-up or
  a memory saving.
- **Comparison table:** directly under the opening paragraph, before Why, a
  before-and-after table on a named deck: the same
  machine and solver for both runs, the number of runs, the base commit and
  the branch. It shows wall time for a speed-up and peak memory for a
  memory saving. CI measures neither speed nor memory, so the table is the
  only record of the improvement.
- A performance change gets no CHANGELOG entry: `CONTRIBUTING.md`,
  Changelog, excludes results-neutral changes with no DSL or output effect.
