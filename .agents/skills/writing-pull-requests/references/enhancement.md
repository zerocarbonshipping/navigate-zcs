<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing an enhancement pull request

- **What changed** leads with the user-visible surface: the DSL attributes,
  commands, keywords and report properties added or changed, the
  reference-manual pages updated, and the changelog entry. A new attribute
  or command lives in four places (`AGENTS.md`, What a change touches); name
  each.
- **Why** links the issue where the design was agreed, for a large feature.
- **Assumptions and scope** carries a `### Decisions` subsection for the
  choices made during the work, each with its reason.
- **When outputs move**, Verification carries a results table: the
  quantities and years that matter, base → branch, with the commit and the
  deck. Explain each shift by the mechanism that causes it.
