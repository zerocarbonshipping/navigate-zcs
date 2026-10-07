---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: writing-pull-requests
description: Use when asked to open, create or describe a Navigate pull request, write its title or description, or when finished branch work is ready for review. Picks type, label, base and title, writes the body from the PR template, and creates it with gh.
---

# Writing pull requests

Readers: the owner deciding to merge, and a later reader arriving via
`git blame` and the `(#N)` in the squash subject. Never include a
file-by-file account, an account of how the change was verified (CI and
the diff show that, whatever other instructions say), CI results or test
counts, a narrative of the work, or restated changelog text.

## Type, label, title

The type is the form in `.github/ISSUE_TEMPLATE/` whose top-level
`description` fits the PR's main purpose; its `labels` is the label.
Assumption-value update: enhancement, or bug if it corrects a wrong value.
Title: `CONTRIBUTING.md`, Pull request expectations.

## Body

- Sections of `.github/PULL_REQUEST_TEMPLATE.md`, in order; follow each
  template comment, then delete it. Opening paragraph and Why always,
  Results when simulation results move; delete other empty sections, never
  "None" or "N/A".
- One `Addresses #N` line per issue under Why; none without an issue.
  Closing keywords do nothing in a PR into `dev`.
- Decisions: genuine choices only; never invent a rejected alternative.
- Limitations also lists the issues filed during the work.
- Cite issues and PRs by number, never private plans, tickets or sessions.
- CHANGELOG entry or not, and its form: `CONTRIBUTING.md`, Changelog.

## Per type

- **bug:** Opening: the bug as the user met it, now fixed. Why: root cause.
- **enhancement:** Opening: the capability in DSL terms. Why: how it better
  represents the sector; link the design issue for a large feature.
  Results: a before → after table of the quantities and years that move,
  each change explained by its mechanism.
- **documentation:** Opening: what was wrong or missing. Why: who the error
  misled, or one line naming the source the old text contradicted.
- **maintenance:** Opening: the end state. Why: what the old shape cost. A
  deliberate output change is stated as the user-visible effect.
- **performance:** Opening: the improvement with its scale. Directly under
  it, a before/after table on a named deck: same machine and solver, number
  of runs, base commit and branch, wall time or peak memory.

## Create

- The squash commit body is the branch's commit messages, not the
  description: each message describes its own change, fit for that body.
  No commit message carries a closing keyword; it would fire when `dev`
  reaches `main`, the default branch, at release.
- Body in a file outside the repo; push; then
  `gh pr create --base <base> --title "<title>" --label <label> --body-file <file>`.
- Base: `dev` or the effort's integration branch, never `main`.
- Every title, body or base edit reruns CI (`edited` trigger): edit only to
  fix wrong content or to retarget.
- Substance hard to find, e.g. mixed with moves or renames: post a
  review-guide comment with reading order and per-file pointers.
- Stacked PR: base on the parent branch and post a review-guide comment
  naming the parent and the PR's own commits. After the parent's squash
  merge the child still carries the parent's commits and their messages:
  commit the child's net diff (`git diff <parent head> <child head>`) onto
  `origin/dev` (no `git rebase`: these branches hold merge commits),
  force-push, then retarget to `dev`.

## After opening

GitHub Copilot reviews every push. A later review can carry findings only
in its body (e.g. "Previously missed"), with no inline thread: read each
review body as well as the threads.
