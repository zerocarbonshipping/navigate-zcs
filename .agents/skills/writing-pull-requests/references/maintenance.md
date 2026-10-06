<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a maintenance pull request

- **Opening paragraph:** the end state, as the code now stands. Usually
  "No user-visible effect."
- **Why:** what the old shape cost.
- **Evidence:** the neutrality proof, where `CONTRIBUTING.md`, Evidence in
  a pull request, requires one. A new test or lint rule also gets the
  deliberate-break table described there.
- A maintenance change gets no CHANGELOG entry. The exception is an effect
  a user sees anyway, such as a renamed logger in the log output; that gets
  an entry.
