---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: filing-issues
description: Use when asked to file, open or write up a GitHub issue on Navigate, or when a defect, gap or debt found during other work should be recorded. Picks the type, applies its issue form by hand and creates the issue with gh.
---

# Filing issues

Found during another task: keep the current branch clear of the problem,
file it, then resume the task.

**Confirm on dev first:** `git fetch`, then read `origin/dev:<path>`; your
branch may be behind a fix that a search does not find.

**Then search:** `gh issue list --state all --search "<terms>"` and
`gh pr list --state all --search "<terms>"`. Existing issue: comment only
what it lacks, such as new evidence or a PR that fixed part of it; never
close it. Open PR that addresses it: don't file. A closed, unmerged PR
does not stop filing.

## Form

The forms are in `.github/ISSUE_TEMPLATE/`. The type is the form whose
top-level `description` fits; its `labels` is the label. A question that
fits no form: blank issue, `--label question`.

`gh` bypasses forms, so render one by hand: each `body` field's `label` is a
`###` heading, in form order, filled as its `description` says;
`type: markdown` gives none. Required fields always present; empty optional
ones omitted, never "N/A".

## Rules

- Problem, never solution: what is wrong, intended behaviour or property,
  evidence, location. No fix, design, test to write or verification. A
  fresh session chooses the solution from the issue alone.
- Standalone: no reference to a conversation, plan or scratch file; cite
  issues and PRs by number.
- Evidence holds on `origin/dev`. Code-reading evidence comes from
  `git show origin/dev:<path>`. Run evidence needs a worktree of
  `origin/dev` with its own `make pip-setup` only when your branch differs
  from `origin/dev` in the code or assumptions involved: `navigate` on PATH
  is one checkout's editable install, and a worktree without its own
  environment imports the primary checkout's code.
- Pin `origin/dev @ <short SHA>`: in Version for a bug, otherwise next to
  the evidence; none for an enhancement without code evidence.
- Locations: code as `path:line` plus symbol, documentation as page and
  heading.
- One problem per issue; a second problem gets its own issue, linked as
  `#N`. No assignee or milestone unless asked. No test-run statistics.
- Title under ~80 characters, no prefix or type tag. Bug, documentation,
  performance: the symptom as the user meets it, performance with scale.
  Maintenance, enhancement: the intended outcome as behaviour or property,
  not mechanism.

## Per type

- **bug:** Reproduce on a copy outside the repo. Includes resolve relative
  to the deck's own directory, and scenario, regression and guardrail decks
  include `../0_includes/*.inc`: copy everything the deck reaches through
  relative includes with the layout kept, e.g. the parent folder. Run
  `<checkout>/.venv/bin/navigate <copy>/<deck>.nav -d <checkout>/assumptions -s`.
- **documentation:** Code wrong: a bug. Several mismatches of one kind found
  in one pass make one issue. The reference manual covers user-visible
  behaviour only, no modelling derivations; internals belong in root files
  and folder READMEs.
- **enhancement:** A DSL idea goes under Considerations as a known option.

## Create

Body in a file outside the repo, then
`gh issue create --title "<title>" --label <label> --body-file <file>`.
