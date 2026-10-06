---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: writing-pull-requests
description: Opens Navigate pull requests when asked to open, create or describe one, to write its title or description, or when finished work on a branch is ready for review. Picks the type, label, base and title, writes a description for the reviewer and the later git-blame reader from the pull request template and a per-type reference, and creates it with gh.
---

# Writing pull requests

A pull request description has two readers. The reviewer decides whether to
merge: what the change does and its user-visible effect, why, which choices
they might make differently, and evidence beyond what CI shows. A later
reader arriving from `git blame` needs why, the alternatives rejected, and
the known limits.

So the description never carries a file-by-file account of the diff, CI
results, a narrative of how the work went, or restated changelog text; the
diff, the checks and the CHANGELOG diff show those.

`.github/PULL_REQUEST_TEMPLATE.md` sets the sections. `gh` does not apply
it, so this procedure applies it by hand.

Copy this checklist and tick it off:

```
- [ ] 1. Pick the type
- [ ] 2. Write the title
- [ ] 3. Read the type's reference and write the body
- [ ] 4. Create the pull request and report its URL
- [ ] 5. For a large diff, post a review guide
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

One imperative sentence stating the outcome, with no prefix, under about 72
characters (`CONTRIBUTING.md`, Pull request expectations). It becomes the
squash-commit subject. For example: "Reject a negative bunkering limit when
the deck is read". For a single-commit pull request, make the commit subject
equal the title.

## 3. Read the type's reference and write the body

Read the reference for the type, from the table above, then the template.
Follow each HTML comment and leave the comments and the SPDX header out of
the body.

- Only the opening paragraph and Why are required. Delete an optional
  section that has nothing to say; never write "None" or "N/A".
- Length follows the change: a small fix may be the opening paragraph and
  Why alone.
- Put each issue on its own `Addresses #N` line under Why. With no issue,
  write no such line and nothing in its place. Closing keywords never fire:
  pull requests merge into `dev`, and GitHub honours them only on the
  default branch, `main`. The issue is closed by hand after the merge.
- A rejected approach goes in Decisions, not in a story of the work.

## 4. Create the pull request and report its URL

Write the body to a file outside the repository, push the branch, then:

```sh
gh pr create --base <base> --title "<title>" --label <label> --body-file <file>
```

The base is `dev`, or the integration branch of the larger effort the work
belongs to; never `main`. A stacked pull request bases on its parent branch
and is retargeted to `dev` once the parent merges.

Every edit to the title, body or base reruns CI, because the workflows
trigger on `edited`. Edit only to fix wrong content or to retarget. Report
the URL that `gh pr create` prints.

## 5. For a large diff, post a review guide

Right after creating the pull request, post one comment with
`gh pr comment`: where the substance is, what is mechanical (moves,
renames), and a reading order. It is a comment, not part of the
description, because the description is the durable record and the guide
matters only during review.

## Rules

- The description stands alone. Cite issues and pull requests by number;
  never cite private plans, tickets, sessions or scratch files.
- Name a file or symbol only where it is needed to understand the design or
  to point to the substance. Put code, paths and symbols in backticks.
- Write plain, short declarative sentences.

## Evidence

Evidence holds only what CI does not show.

- **Neutrality** is shown base versus branch, for every deck under
  `simulations/examples/` and `tutorials/` whose run reaches the changed
  code. Report CSVs must be byte-identical and xlsx reports identical cell
  by cell; xlsx bytes differ between saves. For a deck that writes no
  report, pickle every node's profile and expectation after a full run on
  base and on branch, and compare.
- The regression suite is not a neutrality proof: its baselines cover few
  decks and carry a noise floor (`tests/regression/README.md`).
- A change that touches nothing under `navigate/` or `assumptions/`, no
  deck or include, and no dependency in `pyproject.toml` needs no
  neutrality evidence. Say so in one line, or drop Evidence when nothing
  else applies.
- Naming what a new test pins is fine; counting tests is not.
- What was not run lists only checks a reviewer would expect and that were
  skipped. Never fill it by inference.
- When results move, show the difference, explain its cause, and name the
  baseline-regeneration commit.
