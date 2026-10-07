<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a performance pull request

- **Opening paragraph:** the speed-up, with its scale, followed by a
  before-and-after timing table on a named deck: the same machine and
  solver for both, the number of runs, the base commit and the branch. CI
  does not measure speed, so the table is the only record of it.
- A speed-up or memory saving a deck author would notice in a run gets a
  CHANGELOG entry under Changed; a minor one gets none.
