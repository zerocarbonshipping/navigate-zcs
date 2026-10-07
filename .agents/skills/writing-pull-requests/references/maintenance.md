<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a maintenance pull request

- **Opening paragraph:** the end state, as the code now stands, then any
  deliberate change to log, console or report output as its user-visible
  effect. "No user-visible effect." only when the output is unchanged.
- **Why:** what the old shape cost.
- A deliberate change to output gets a CHANGELOG entry, because console,
  log and report output are entry-worthy (`CONTRIBUTING.md`, Changelog).
  Otherwise a maintenance change gets none.
