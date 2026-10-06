<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a maintenance pull request

- **What changed** states the end state reached, as the code now stands,
  and what was reworked to get there, with the reason.
- **Verification** carries the neutrality proof, base versus branch, with
  the base commit and the decks run. When no file under `navigate/`
  changed, one line saying so is the proof.
- A new test or lint rule gets a deliberate-break table: each break,
  applied alone, and the failure it caused (#441).
- A maintenance change gets no changelog entry; say so, with the reason.
  The exception is an effect a user sees anyway, such as a renamed logger in
  the log output.
- Debt found beyond the task goes in a follow-up issue, linked under
  Assumptions and scope. It does not go into the pull request.
