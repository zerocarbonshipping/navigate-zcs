---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: writing-pull-requests
description: Use when asked to open, create or describe a Navigate pull request, write its title or description, or when finished branch work is ready for review. Picks type, label, base and title, writes the body from the PR template, and creates it with gh.
---

# Writing pull requests

Readers: the reviewer deciding to merge, and a later reader arriving via
`git blame` and the `(#N)` in the squash subject. Never include a
file-by-file account, CI results or test counts, a narrative of the work, or
restated changelog text.

## Type, label, title

- **bug:** behaviour differs from the reference manual, a docstring or the
  model's intent.
- **enhancement:** changes what a user can do or sees.
- **documentation:** text only.
- **maintenance:** improves code without changing what the model computes; a
  deliberate output change is allowed, stated as a user-visible effect.
- **performance:** speed or memory, not results.

Mixed PR: its main purpose. Assumption-value update: enhancement, or bug if
it corrects a wrong value. Label: `labels` of the matching form in
`.github/ISSUE_TEMPLATE/`. Title: follow `CONTRIBUTING.md`.

## Body

- Sections of `.github/PULL_REQUEST_TEMPLATE.md`, in order; follow each
  template comment, then delete it. Opening paragraph and Why always;
  Results when simulation results move. Delete other empty sections, never
  "None" or "N/A". Length follows the change.
- One `Addresses #N` line per issue under Why; none without an issue.
  Closing keywords never fire (PRs merge into `dev`; GitHub honours them only
  on `main`): close the issue by hand after the merge.
- Decisions: genuine choices only; never invent a rejected alternative.
- Cite issues and PRs by number, never private plans, tickets or sessions.

## Per type

- **bug:** Opening: the bug as the user met it, now fixed. Why: root cause.
  A user-visible bug: CHANGELOG under Fixed, ending with the issue number if
  any.
- **enhancement:** Opening: the capability in DSL terms; a new attribute or
  command lives in four places (`AGENTS.md`, What a change touches). Why: how
  it better represents the sector; link the design issue for a large feature.
  Results: a before → after table of the quantities and years that move,
  each change explained by its mechanism. CHANGELOG under Added or Changed.
- **documentation:** Opening: what was wrong or missing. Why: what the
  opening leaves out, e.g. who the error misled; otherwise one line naming
  the source the old text contradicted. Reference-manual errors get a
  CHANGELOG entry like bugs; other documentation none.
- **maintenance:** Opening: the end state; Why: what the old shape cost. A
  deliberate output change is the user-visible effect, with a CHANGELOG
  entry; otherwise "No user-visible effect." and no entry.
- **performance:** Opening: the improvement with its scale. Directly under
  it, a before/after table on a named deck: same machine and solver, number
  of runs, base commit and branch, wall time or peak memory; CI measures
  neither. No CHANGELOG entry: `CONTRIBUTING.md` excludes results-neutral
  changes with no DSL or output effect.

## Create

- The squash commit body is the branch's commit messages, not the
  description: no unsquashed "address review" commits.
- Body in a file outside the repo; push; then
  `gh pr create --base <base> --title "<title>" --label <label> --body-file <file>`.
- Base: `dev` or the integration branch of the larger effort, never
  `main`. A stacked PR bases on its parent branch, retargeted to `dev` once
  the parent merges.
- Every title, body or base edit reruns CI (`edited` trigger): edit only to
  fix wrong content or to retarget.
- Substance hard to find, e.g. mixed with moves or renames: post a
  review-guide comment with reading order and per-file pointers. The opening
  still says in one line which part is mechanical.
- A stacked PR always posts a review-guide comment naming its parent and its
  own commits.
