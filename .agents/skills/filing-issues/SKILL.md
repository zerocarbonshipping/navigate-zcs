---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: filing-issues
description: Files GitHub issues on the Navigate repository with gh. Use when asked to file, open, report or write up an issue, or when a defect, gap or piece of debt found during other work should be recorded. Reads the matching issue form for its label and sections, then a per-type reference for bug, enhancement, documentation, maintenance or performance.
---

# Filing issues

An issue records one problem for a reader who has none of the context it was
found in. The issue forms in `.github/ISSUE_TEMPLATE/` set each type's label,
its sections, their order, which are required and what goes in each. `gh`
bypasses the forms, so this procedure reads them and applies them by hand.

An issue states the problem, never the solution. It gives what is wrong, the
intended behaviour or property, the evidence and the location as facts. It
never prescribes a fix, a design, an implementation, the test to write or how
to verify the fix; the test suite, run by CI, proves a fix. A fresh session
that reads only the issue must be able to understand the problem and choose
the solution itself. Facts the solver should keep in mind, such as
constraints, related code paths, pitfalls, things already ruled out and
options already known, go under Considerations, with no option recommended.

Copy this checklist and tick it off:

```
- [ ] 1. Search for an existing issue or pull request
- [ ] 2. Pick the type
- [ ] 3. Read the form
- [ ] 4. Read the type's reference
- [ ] 5. Write the title
- [ ] 6. Write the body and create the issue
```

## 1. Search for an existing issue or pull request

```sh
gh issue list --state all --search "<keywords>"
gh pr list --state all --search "<keywords>"
```

Search with the symbol, file, attribute or error text as well as plain words.
If an issue covers the problem, comment on it with `gh issue comment`
instead of filing. If a pull request already addresses it, link that pull
request rather than filing.

## 2. Pick the type

- **bug:** behaviour that differs from the reference manual, a docstring or
  the model's intent.
- **enhancement:** changes what a user can do or sees.
- **documentation:** fixes text only.
- **maintenance:** improves the code without changing what the model
  computes; a deliberate change to its output is allowed and is stated as a
  user-visible effect.
- **performance:** changes speed or memory, not results.

| Type | Form |
|---|---|
| bug | `01-bug.yml` |
| enhancement | `02-enhancement.yml` |
| documentation | `03-documentation.yml` |
| maintenance | `04-maintenance.yml` |
| performance | `05-performance.yml` |

A question that fits no type is a blank issue with a free-form body and
`--label question`; `config.yml` keeps blank issues enabled.

## 3. Read the form

Read `.github/ISSUE_TEMPLATE/<form>`. Its top-level `labels` value is what
goes to `--label`. Each entry under `body` becomes one section of the issue,
except a `type: markdown` entry, which produces none:

- its `label` is a `### ` heading, in form order;
- its `description` says what goes under the heading;
- a field with `required: true` is always present;
- an optional field with nothing to say is left out, never written as "N/A".

## 4. Read the type's reference

- [references/bug.md](references/bug.md)
- [references/enhancement.md](references/enhancement.md)
- [references/documentation.md](references/documentation.md)
- [references/maintenance.md](references/maintenance.md)
- [references/performance.md](references/performance.md)

## 5. Write the title

- A bug, documentation or performance title states the symptom as the user
  meets it; a performance title gives its scale. Examples: "Fuel cost report
  is empty when a deck sets no carbon price", "Ports deck takes ten minutes
  to parse a thousand-port network".
- A maintenance or enhancement title states the intended outcome as a
  behaviour or a property, not the mechanism that would reach it. Examples:
  "Let a deck set a bunkering limit per port", "Keep every package's imports
  within its layer".
- Every title is one specific sentence, under about 80 characters, with no
  prefix and no type tag. The detail goes in the body.

## 6. Write the body and create the issue

Write the body to a temporary file outside the repository, then:

```sh
gh issue create --title "<title>" --label <label> --body-file <file>
```

The label is passed explicitly because `gh` does not apply the form.

## Rules for every issue

- The issue stands alone. Its reader has no session context: state the
  problem, the evidence and the stakes in full, with no reference to a
  conversation, a plan or a scratch file.
- Pin the commit. A bug pins it in the form's Version field. Any other type
  pins it next to the evidence, as `<branch> @ <short SHA>`. An enhancement
  with no code evidence needs no pin.
- Give a location as `path:line` plus the symbol name, for example
  `navigate/core/bounds.py:50` (`Bounds.check_exclusive`). The line can
  drift; the commit and the symbol keep it findable.
- Link related issues and pull requests as `#N`.
- One problem per issue. A second problem found along the way gets its own
  issue, linked from the first.
- No assignee or milestone unless asked.
- No test-run statistics, such as suite pass counts.
- Write plain, short declarative sentences. Put code, paths and symbols in
  backticks, and commands and trimmed output in fenced blocks.
