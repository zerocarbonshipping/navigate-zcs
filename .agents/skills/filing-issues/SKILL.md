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

Copy this checklist and tick it off:

```
- [ ] 1. Search for an existing issue
- [ ] 2. Pick the type
- [ ] 3. Read the form
- [ ] 4. Read the type's reference
- [ ] 5. Write the title
- [ ] 6. Write the body and create the issue
- [ ] 7. Report the issue URL
```

## 1. Search for an existing issue

```sh
gh issue list --state all --search "<keywords>"
```

Search with the symbol, file, attribute or error text as well as plain words.
If an issue covers the problem, comment on it with `gh issue comment`
instead of filing.

## 2. Pick the type

| Type | Form | Label |
|---|---|---|
| bug | `01-bug.yml` | `bug` |
| enhancement | `02-enhancement.yml` | `enhancement` |
| documentation | `03-documentation.yml` | `documentation` |
| maintenance | `04-maintenance.yml` | `maintenance` |
| performance | `05-performance.yml` | `performance` |

Each form's top-level `description` says what the type covers. A question
that fits no type is a blank issue with a free-form body and no label;
`config.yml` keeps blank issues enabled.

## 3. Read the form

Read `.github/ISSUE_TEMPLATE/<form>`. Each entry under `body` becomes one
section of the issue:

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

- A bug or documentation title states the symptom as the user meets it:
  "A FLEXIBLE intensity regulation with no regulated term and a literal
  threshold crashes the flexibility transfer" (#376), "Reference manual
  defaults and input kinds disagree with the Producer, Source and Technology
  setters" (#425).
- A maintenance or enhancement title states the outcome as an imperative:
  "Type the report reductions without a bare dict" (#415), "Import the
  assignment helpers through navigate.core everywhere in the package" (#423).
- Every title is one specific sentence, with no prefix and no type tag.

## 6. Write the body and create the issue

Write the body to a temporary file outside the repository, then:

```sh
gh issue create --title "<title>" --label <label> --body-file <file>
```

The label is passed explicitly because `gh` does not apply the form. A blank
issue omits `--label`.

## 7. Report the issue URL

Report the URL that `gh issue create` prints.

## Rules for every issue

- The issue stands alone. Its reader has no session context: state the
  problem, the evidence and the stakes in full, with no reference to a
  conversation, a plan or a scratch file.
- Pin the commit the evidence comes from, as `dev @ <short SHA>`.
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
