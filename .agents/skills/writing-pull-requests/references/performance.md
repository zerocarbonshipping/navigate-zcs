<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a performance pull request

- **Verification** gives before and after timings on a named deck, in a
  table: the same machine and solver for both, the number of runs, and the
  base and branch commits.
- Verification also shows results neutrality, base versus branch:
  byte-identical report CSVs, xlsx reports identical cell by cell, and
  identical profile and expectation dumps for decks that write no report.
  A change that moves results says so and explains the difference.
- A change in speed or memory alone gets no changelog entry; say so.
