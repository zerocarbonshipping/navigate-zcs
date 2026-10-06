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
- [ ] 5. Post a review guide if the substance is hard to find
```

## 1. Pick the type

- **bug:** behaviour that differs from the reference manual, a docstring or
  the model's intent.
- **enhancement:** changes what a user can do or sees.
- **documentation:** fixes text only.
- **maintenance:** improves the code without changing what the model
  computes; a deliberate change to its output is allowed and is stated as a
  user-visible effect.
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

Follow the title rule in `CONTRIBUTING.md`, Pull request expectations. For
example: "Reject a negative bunkering limit when the deck is read".

## 3. Read the type's reference and write the body

Read the reference for the type, from the table above, then the template.
Follow each HTML comment and leave the comments out of the body.

- The opening paragraph and Why are always required; Evidence is required
  as the template says. Delete any other empty section; never write "None"
  or "N/A".
- Length follows the change: a small fix may be the opening paragraph and
  Why alone.
- Put each issue on its own `Addresses #N` line under Why. With no issue,
  write no such line and nothing in its place. Closing keywords never fire:
  pull requests merge into `dev`, and GitHub honours them only on the
  default branch, `main`. The issue is closed by hand after the merge.
- Decisions holds only genuine choices. Never invent a rejected
  alternative. A design explanation with no alternative belongs in the
  opening paragraph or Why. A rejected approach goes in Decisions, not in a
  story of the work.

## 4. Create the pull request and report its URL

The squash commit carries the branch's commit messages, not this
description; a later reader reaches the description through the `(#N)` in
the commit subject. Keep the branch's commit messages fit for that history:
no "address review" or "fix typo" commits left unsquashed where a reader
would meet them.

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

## 5. Post a review guide if the substance is hard to find

Post one when the diff mixes mechanical moves or renames with substantive
changes, or a reviewer could not find the substance from the file list
alone. Right after creating the pull request, post one comment with
`gh pr comment` holding the reading order and per-file pointers. A stacked
pull request says there which pull request it builds on and which commits
are its own.

The guide is a comment because the description is the record of the change
on GitHub; the guide only helps the review. The description still says, in
one line of the opening paragraph, which part is mechanical and which is
substance.

## Rules

- The description stands alone. Cite issues and pull requests by number;
  never cite private plans, tickets, sessions or scratch files.
- Name a file or symbol only where it is needed to understand the design or
  to point to the substance. Put code, paths and symbols in backticks.
- Write plain, short declarative sentences.

## Evidence

The standard is `CONTRIBUTING.md`, Evidence in a pull request. Beyond it:

- A change that only reads state and writes none may argue in one sentence
  why a profile dump cannot differ, instead of taking one.
- Never invent or reconstruct output. Rerun the command, or say the output
  is not at hand.
