---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: writing-pull-requests
description: Writes and opens GitHub pull requests on the Navigate repository with gh. Use when asked to open, create or describe a pull request, or to write its title or description, or when finished work on a branch is ready for review. Sets the base, label and title, fills the pull request template, and reads a per-type reference for bug fixes, enhancements, documentation, maintenance or performance.
---

# Writing pull requests

A pull request description is read by a reviewer, and later by anyone
tracing the squash commit, with none of the context the work was done in.
`.github/PULL_REQUEST_TEMPLATE.md` sets its sections; `gh` does not apply
the template, so this procedure reads it and applies it by hand.

Copy this checklist and tick it off:

```
- [ ] 1. Pick the type
- [ ] 2. Write the title
- [ ] 3. Read the type's reference and write the body
- [ ] 4. Create the pull request and report its URL
```

## 1. Pick the type

- **bug:** behaviour that differs from the reference manual, a docstring or
  the model's intent.
- **enhancement:** changes what a user can do or sees.
- **documentation:** fixes text only.
- **maintenance:** leaves behaviour as it is.
- **performance:** changes speed or memory, not results.

A mixed pull request takes the type of its main purpose. An
assumption-value update is an enhancement, or a bug when it corrects a
wrong value. The label is the `labels` value of the matching issue form in
`.github/ISSUE_TEMPLATE/`.

| Type | Form | Reference |
|---|---|---|
| bug | `01-bug.yml` | [references/bug.md](references/bug.md) |
| enhancement | `02-enhancement.yml` | [references/enhancement.md](references/enhancement.md) |
| documentation | `03-documentation.yml` | [references/documentation.md](references/documentation.md) |
| maintenance | `04-maintenance.yml` | [references/maintenance.md](references/maintenance.md) |
| performance | `05-performance.yml` | [references/performance.md](references/performance.md) |

## 2. Write the title

One imperative sentence stating the outcome, with no prefix
(`CONTRIBUTING.md`, Pull request expectations): "Move the power-capacity
check's scope gating into the fleet domain" (#439). For a single-commit pull
request, make the commit subject equal the title.

## 3. Read the type's reference and write the body

Read the reference for the type chosen in step 1, from the table above; it
says what that type's sections must carry. Read
`.github/PULL_REQUEST_TEMPLATE.md`. Use its `## ` sections, in order,
and follow the guidance in each HTML comment. Leave the comments and the
SPDX header out of the body. A section with nothing to say says so in one
line. `### ` subheadings, bullets and tables are welcome inside a section.

Link each issue the pull request addresses on its own `Addresses #N` line
under Why. With no issue, write no line and no "No issue is filed".
Closing keywords never fire, because pull requests merge into `dev` and
GitHub honours them only on the default branch, so the issue is closed by
hand after the merge.

## 4. Create the pull request and report its URL

Write the body in full to a temporary file outside the repository, push the
branch, then:

```sh
gh pr create --base dev --title "<title>" --label <label> --body-file <file>
```

The base is `dev`, or the integration branch of the larger effort the work
belongs to; never `main`, the release branch. A stacked pull request bases
on its parent branch and is retargeted to `dev` once the parent merges.

Every later edit to the title, body or base reruns CI, because the
workflows trigger on `edited`. Edit only to fix wrong content or to
retarget. Report the URL that `gh pr create` prints.

## Rules for every pull request

- **The description stands alone:** what changed, why, how it was verified,
  and what was assumed or left out. Cite issues and pull requests by
  number; never cite private plans, tickets, sessions or scratch files.
- **Verification states only what CI does not show.**
  - Never list the suites CI runs, pass counts or "lint passes". A run CI
    does not do, such as a reference scenario under
    `simulations/scenarios/`, is stated with what it showed.
  - Do state, where they apply:
    - neutrality evidence, base versus branch, for the affected decks:
      every deck under `simulations/examples/` and `tutorials/` whose run
      reaches the changed code. The evidence is byte-identical report CSVs
      and xlsx reports identical cell by cell. For a deck that writes no
      report, pickle every node's profile and expectation after a full run
      on base and on branch, and compare;
    - base-versus-branch CLI runs for a new or changed deck error;
    - a results-difference table with an explanation, when results move;
    - a deliberate-break table for a new check: each break, applied alone,
      and the failure it caused;
    - manual checks;
    - what was not run: only checks a reviewer would expect and that were
      skipped. Never fill it by inference.
  - The regression suite is not a neutrality proof: its baselines cover few
    decks and carry a noise floor (`tests/regression/README.md`).
  - A change that touches nothing under `navigate/` or `assumptions/`, no
    deck or include, and no dependency in `pyproject.toml` needs no
    neutrality evidence; Verification says so in one line.
  - Naming what a new test pins is fine; counting tests is not.
  - When nothing goes beyond CI, the section says so in one line.
- **When simulation results move,** Verification names the
  baseline-regeneration commit.
- Write plain, short declarative sentences. Put code, paths and symbols in
  backticks.
