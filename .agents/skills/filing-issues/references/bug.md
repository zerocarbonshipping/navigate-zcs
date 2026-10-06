<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a bug

- **Confirm the defect still exists** on the current tip of the base branch
  before filing (`git fetch`, then reproduce on `origin/dev`), and pin that
  commit. A defect seen on an older commit may already be fixed.
- **Say which kind it is**, in the Description: a crash, a wrong result, a
  deck accepted silently that should fail, or a valid deck rejected. Give
  expected versus actual, and why it matters to a deck author or a reader
  of the output.
- **Reproduce it before filing.** Prefer a minimal deck, or an edit to a
  copy of an existing deck such as `simulations/examples/example_1`, shown
  as a diff (#376). Copy the deck folder outside the repository, so the run
  writes no output next to the committed deck, and run it with
  `navigate <copy>/<deck>.nav -d <repo>/assumptions -s`. Give:
  - that exact command;
  - the error or output, trimmed to the lines that show the defect;
  - what the unmodified copy does, so the edit is shown to be the trigger.
- **A defect found by reading code**, with no run, says so. Give the
  argument step by step: which value reaches which operation, and why the
  result is wrong (#344).
- **Location** is where the defect is, not only where it surfaces.
- **Proposed resolution** is optional. When given, it names the fix, says
  whether it moves results, and names the test that would pin it. When the
  right fix is open, it lists the options and what each would entail.
