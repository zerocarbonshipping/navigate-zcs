---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: writing-pull-requests
description: Writes and opens GitHub pull requests on the Navigate repository with gh. Use when asked to open, create or describe a pull request, or to write its title or description. Sets the base, label and title, fills the pull request template, and reads a per-type reference for bug fixes, enhancements, documentation, maintenance or performance changes.
---

# Writing pull requests

A pull request description is read by a reviewer, and later by anyone
tracing the squash commit, with none of the context the work was done in.
`.github/PULL_REQUEST_TEMPLATE.md` sets its sections; `gh` does not apply
the template, so this procedure reads it and applies it by hand.

Copy this checklist and tick it off:

```
- [ ] 1. Pick the base
- [ ] 2. Pick the type
- [ ] 3. Write the title
- [ ] 4. Write the body
- [ ] 5. Link the issues
- [ ] 6. Create the pull request
- [ ] 7. Report the pull request URL
```

## 1. Pick the base

`dev`, or the integration branch of the larger effort the work belongs to.
Never `main`, the release branch.

## 2. Pick the type

The type sets the label, passed with `--label`, and the reference to read.

| Type | Label | Reference |
|---|---|---|
| bug fix | `bug` | [references/bug.md](references/bug.md) |
| enhancement | `enhancement` | [references/enhancement.md](references/enhancement.md) |
| documentation | `documentation` | [references/documentation.md](references/documentation.md) |
| maintenance | `maintenance` | [references/maintenance.md](references/maintenance.md) |
| performance | `performance` | [references/performance.md](references/performance.md) |

## 3. Write the title

One imperative sentence stating the outcome, with no prefix and no type tag:
"Move the power-capacity check's scope gating into the fleet domain" (#439).
Pull requests are squash-merged, so the title becomes the commit subject.

## 4. Write the body

Read `.github/PULL_REQUEST_TEMPLATE.md`. Use its `## ` sections, in order,
and follow the guidance in each HTML comment. Leave the comments and the
SPDX header out of the body. A section with nothing to say says so in one
line. `### ` subheadings, bullets and tables are welcome inside a section.

## 5. Link the issues

Write `Addresses #N` under Why. Closing keywords never fire: pull requests
merge into `dev`, and GitHub honours them only on the default branch,
`main`. Close the issue by hand after the merge.

## 6. Create the pull request

Write the body in full to a temporary file outside the repository, push the
branch, then:

```sh
gh pr create --base <base> --title "<title>" --label <label> --body-file <file>
```

Every later edit to the title or body reruns CI, because the workflows
trigger on `edited`. Edit only to fix wrong content.

## 7. Report the pull request URL

Report the URL that `gh pr create` prints.

## Rules for every pull request

- **The description stands alone:** what changed, why, how it was verified,
  and what was assumed or left out. It refers to no conversation, plan or
  scratch file.
- **Verification states only what CI does not show.**
  - Never list the suites run, pass counts or "lint passes". CI reports
    those on the pull request.
  - Do state, where they apply:
    - neutrality evidence, base versus branch: byte-identical report CSVs,
      xlsx reports identical cell by cell, and, for decks that write no
      report, identical dumps of every profile and expectation after a full
      run. The regression suite has a noise floor and is not a proof
      (`tests/regression/README.md`);
    - base-versus-branch CLI runs for a new or changed deck error;
    - a results-difference table with an explanation, when results move;
    - a deliberate-break table for a new check: each break, applied alone,
      and the failure it caused;
    - manual checks;
    - what was not run.
  - Naming what a new test pins is fine; counting tests is not.
  - When nothing goes beyond CI, the section says so in one line.
- **When simulation results move,** explain the difference, and regenerate
  the baselines with `make regen-regression` in a commit of their own
  (`AGENTS.md`).
- **CHANGELOG:** state the entry, or why there is none
  (`CONTRIBUTING.md`, Changelog).
- **Assumption-value changes** carry references or a justification, whatever
  the type.
- Write plain, short declarative sentences. Put code, paths and symbols in
  backticks.
