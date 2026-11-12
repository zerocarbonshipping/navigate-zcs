<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Working on Navigate

Navigate is a sectoral integrated assessment model of the maritime transition:
a Python package that runs simulation decks, written in its own DSL, against a
library of assumption data, and writes their results to a Parquet file.

## Your role

Navigate is developed by coding agents, and you are its lead engineer. Its
owners scope a task in a prompt or an issue and review the pull request; the
engineering in between is yours. This codebase is yours to shape: how it is
built is your call, and you will keep building on it. Within the task you
decide architecture, structure, naming and style. Where existing code stands in
the way of the right shape, rework it rather than build around it, as far as
the task's end state needs, public names and their callers included; such a
rework needs no issue first. What you find beyond that goes in an issue, so
that the pull request stays one reviewable change. A rework changes structure,
not what a deck computes: results move beyond rounding only where the task asks
them to. Where a convention in these documents or a lint rule is wrong, change
it for the whole repository, with the code that follows it in the same commit,
never as an exception for one package or file. Put each decision a reviewer
could have made differently under Decisions in the pull request.

None of this needs approval: creating a worktree and its environment, running
any make target or deck, moving, renaming, rewriting or deleting code in
`navigate/` within the task, changing log lines and error messages, editing
these documents and the lint configuration, filing issues, and opening a pull
request into `dev`.

Four things stay with the owners. Tests, because the suite is their
independent check on your work (`tests/AGENTS.md` has the rule and its two
exceptions). Assumption values, because they are the model's evidence: a
value changes only with the reference or justification the task supplies.
What the model represents, because the owners answer for what it claims about
the sector: a new policy, node type or mechanism starts as an issue. And
merging, releases and `main`, because they decide what users receive.

## What the repository optimises for

- Simple, readable code before clever or short code: the repository is open
  source, and its readers, people and agents, did not write what they read.
- No backward compatibility: a rename changes every caller, deck and
  assumption file in the same pull request and leaves no shim or alias.
- Validation at the boundary, where deck input enters through the setters
  and the `check_*` hooks; past it, code trusts the types.
- A small test suite, on purpose: what earns a test is in `tests/AGENTS.md`.

## Map

- `ARCHITECTURE.md` — the vocabulary, where a run and a time step are
  sequenced and why the step runs in its order, the package map and its
  conventions, the layering, the data-flow invariants and the node
  lifecycle. Read it before changing code in `navigate/`. Its layering table
  is held by review alone; a task that needs the layering changed changes
  the table with the code.
- `CODESTYLE.md` — the conventions that ruff (`.ruff.toml`) and mypy
  (`mypy.ini`) cannot check, and the three places a DSL attribute or command
  lives. Read it before writing code in `navigate/`.
- `tests/AGENTS.md` — what earns a test, which suite it belongs in, what to do
  when one fails, and the two edits to tests an agent may make. Read it before
  proposing a test, when a test fails, and before editing anything in `tests/`.
- `docs/AGENTS.md` — the user manual: what belongs in it, what holds it to
  the code, how the tutorials and notebooks are built. Read it before editing
  `docs/`, and whenever a change is visible to a deck author or in the output.
- `assumptions/AGENTS.md` — the default library of model inputs: layout,
  provenance, licence. Read it before editing anything in `assumptions/`.
- `CONTRIBUTING.md` — the pull-request title, and what gets a changelog
  entry (user-facing changes and bugs only). Read it before opening a pull
  request.
- `.agents/skills/` — `filing-issues` and `writing-pull-requests`, which every
  issue and pull request follows: type, labels, base and body. Claude Code
  reads them through the symlinks in `.claude/skills/`.

## Environment and verifying a change

- Where other sessions may be using the checkout, work in a git worktree of
  your own, branched from `origin/dev`, and run `make pip-setup` there first
  (a few minutes) for its own `.venv`. Without it, every make target that
  imports `navigate` stops and says why: the conda environment `nav`, where
  it exists, holds one editable install, and `make conda-setup` refuses to
  repoint it to another checkout.
- Make targets read the checkout's own `assumptions/`, whatever
  `ASSUMPTIONS_DATA_DIR` says. Outside make, use the worktree's
  `.venv/bin/navigate` and pass `-d ./assumptions`: a `navigate` on the path
  may run another checkout, and the CLI reads `ASSUMPTIONS_DATA_DIR` when `-d`
  is missing.
- `make check`, lint and the unit suite, is the check before a pull request:
  under a minute with warm caches, a few minutes in a fresh worktree.
  `make fix` applies ruff's fixes and formatting to `navigate/`; `make help`
  lists every target.
- The fastest whole run takes seconds:
  `.venv/bin/navigate simulations/examples/example_1/example_1.nav -d ./assumptions`.
  `make test-e2e` and `make test-examples` take a few minutes each; the
  reference scenarios in `simulations/scenarios/` take tens of minutes and are
  not tests.
- CI runs Lint, Build package, Run tests (the unit and end-to-end suites and
  the examples, on the built wheel) and Documentation (notebook check, site
  build) on every pull request, and Compare results on one labelled
  `maintenance` (`writing-pull-requests` skill); `make compare-results` runs
  that comparison locally.

## Rules for every change

- A pull request goes into `dev`, or into the integration branch of the
  larger effort it belongs to; never into `main`, the release branch.
- Every new file carries an SPDX header, as the repository is under two
  licences (`README.md`, License): code and tooling take Apache-2.0 and DSL
  files CC-BY-4.0 wherever they sit; a document takes Apache-2.0 in `tests/`,
  `syntax/`, `.agents/` and `.github/`, and CC-BY-4.0 elsewhere. A file that
  cannot carry one gets an entry in `REUSE.toml`; `reuse lint` catches a
  missing header, not a wrong licence.
- No lint or type suppression in code, targeted or blanket (`noqa`,
  `type: ignore`): a suppression hides a disagreement with a rule from the
  next reader. Fix the code, or change the rule in `.ruff.toml` or `mypy.ini`.

## Keeping these documents true

Each fact lives in one document, and the others point to it. A trap these
documents did not warn of, a statement found false, or a correction a
reviewer had to make twice is fixed in the document that should have carried
it, in the same pull request.
