<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing a bug-fix pull request

- **What changed** gives the bug as the user meets it, its root cause, and
  the fix.
- **Verification** shows a base-versus-branch run of the reproduction: the
  same command on both, with the exit code and the trimmed CLI output before
  and after. For a deck that should fail, the branch output shows the error
  the user now gets.
- Name the test that pins the bug and what it asserts. Say that it fails on
  the base.
- A bug in user-visible behaviour gets a changelog entry under Fixed, ending
  with the issue number. State it under What changed.
- If the fix moves results, the results-difference table and the baseline
  commit apply as for any change.
