<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a maintenance pull request

- **Opening paragraph:** the end state, as the code now stands. Usually
  "No user-visible effect."
- **Why:** what the old shape cost.
- **Evidence:** the neutrality proof of SKILL.md, with the base commit and
  the decks run. A new test or lint rule also gets a deliberate-break
  table: each break applied alone, and the failure it caused.
- A maintenance change gets no CHANGELOG entry. The exception is an effect
  a user sees anyway, such as a renamed logger in the log output; that gets
  an entry.
