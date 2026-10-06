<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a bug

A bug is behaviour that differs from what the reference manual, a docstring
or the model's intent says.

- **Say which kind it is**, in the Description: a crash, a wrong result, or
  a deck accepted silently that should fail. Give expected versus actual,
  and why it matters to a deck author or a reader of the output.
- **Reproduce it before filing**, on a named commit. Prefer a minimal deck,
  or a diff against an existing deck such as
  `simulations/examples/example_1` (#376). Give:
  - the exact command, for example `navigate example_1.nav -d ./assumptions -s`;
  - the error or output, trimmed to the lines that show the defect;
  - what the unmodified deck does, so the edit is shown to be the trigger.
- **A defect found by reading code**, with no run, says so. Give the
  argument step by step: which value reaches which operation, and why the
  result is wrong (#344).
- **Location** is where the defect is, not only where it surfaces.
- **Version** is the commit, as `dev @ <short SHA>`.
- **Proposed resolution** is optional. When given, it names the fix, says
  whether it moves results, and names the test that would pin it. When the
  right fix is open, it lists the options and what each would entail.
