---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: filing-issues
description: Use when asked to file, open or write up a GitHub issue on Navigate, or when a defect, gap or debt found during other work should be recorded. Picks the type, applies its issue form by hand and creates the issue with gh.
---

# Filing issues

**Search first:** `gh issue list --state all --search "<terms>"` and
`gh pr list --state all --search "<terms>"`. Existing issue: comment there,
don't file. Open PR that addresses it: link it, don't file. A closed,
unmerged PR does not stop filing. After a merged PR, check the problem
persists on `origin/dev` before deciding not to file.

## Type and form

Forms are in `.github/ISSUE_TEMPLATE/`; the label is the form's top-level
`labels`.

- **bug** (`01-bug.yml`): behaviour differs from the reference manual, a
  docstring or the model's intent.
- **enhancement** (`02-enhancement.yml`): changes what a user can do or sees.
- **documentation** (`03-documentation.yml`): text only.
- **maintenance** (`04-maintenance.yml`): improves code without changing what
  the model computes; a deliberate output change is allowed, stated as a
  user-visible effect.
- **performance** (`05-performance.yml`): speed or memory, not results.
- Fits none: blank issue, `--label question`.

`gh` bypasses forms. Each `body` field's `label` is a `###` heading, in form
order; `type: markdown` gives none. Required fields always present; empty
optional ones omitted, never "N/A".

## Rules

- Problem, never solution: what is wrong, intended behaviour or property,
  evidence, location. No fix, design, test to write or verification; CI's
  tests prove fixes. A fresh session must choose the solution from the issue
  alone. Facts to keep in mind go under Considerations, no option
  recommended.
- Standalone: no reference to a conversation, plan or scratch file.
- Pin the commit: bug in Version, otherwise `<branch> @ <short SHA>` by the
  evidence; none for an enhancement without code evidence.
- Locations: `path:line` plus symbol.
- One problem per issue. No assignee or milestone unless asked. No test-run
  statistics.
- Title under ~80 characters, no prefix or type tag. Bug, documentation,
  performance: the symptom, performance with scale. Maintenance, enhancement:
  the intended outcome as behaviour or property, not mechanism.

## Per type

- **bug:** Confirm on current `origin/dev`; pin that commit. Kind: crash,
  wrong result, bad deck accepted silently, or valid deck rejected. Reproduce
  from a deck copy outside the repo:
  `navigate <copy>/<deck>.nav -d <repo>/assumptions -s`; give the command,
  trimmed output, and what the unmodified copy does. Found by reading code:
  say so, give the argument. Location is the defect, not where it surfaces.
- **documentation:** Quote the text and the source of truth it contradicts:
  setter, `navigate/parser/_attributes.py`/`_commands.py`, or code path.
  Unclear which side is wrong: say so. Code wrong: a bug. The reference
  manual covers user-visible behaviour only, no modelling derivations;
  internals belong in root files and folder READMEs.
- **enhancement:** Motivation and Intended behavior from the user's side, not
  attributes, commands or code; a DSL idea only under Considerations.
  Assumption values need references or a justification.
- **maintenance:** The debt and its cost. Intended state: a property, not
  steps. A grep for scattered sites. "Decide whether…": the decision and why
  it matters, known options under Considerations. Name any output change the
  intended state itself requires.
- **performance:** Prefer a small deck; `simulations/scenarios/` runs take
  ~25 minutes. Measurement: deck, solver, commit, machine; then wall time
  with run count, trimmed profile, or peak memory; or an asymptotic argument.
  Target optional.

## Create

Body in a file outside the repo, then
`gh issue create --title "<title>" --label <label> --body-file <file>`. Do
not report the URL.
