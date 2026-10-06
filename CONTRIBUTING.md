<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Contributing to Navigate

Thank you for your interest in improving Navigate. In principle anything can
be contributed: bug fixes, features, new policies, assumptions, documentation,
and tutorials. Contributions are made by forking the repository and opening a
pull request against the `dev` branch.

## Getting started

1. Fork the repository and clone your fork.
2. Set up a development environment. Feel free to use `make conda-setup` (conda) or
   `make pip-setup` (venv + pip).
3. Create a branch from `dev` for your change.
4. Verify your setup by running `make lint` and `make test-unit`.
5. Skim [ARCHITECTURE.md](ARCHITECTURE.md) for the package map and the
   data-flow invariants contributions must respect.

## What to contribute

Any valuable contribution is welcome.

**Bug fixes** can be submitted directly as a pull request. Describe the bug
and how the fix addresses it. If you have found a bug but do not plan to fix
it yourself, please open an issue instead.

**Large features**, such as new policies, new node types, and major
refactors, should start as an issue. This lets us align on scope and design
before you invest significant effort. Smaller features can be submitted
directly as a pull request.

**Assumption changes** must include references or a justification for the new
values, so that the provenance of the model inputs stays traceable.

## Pull request expectations

- Target the `dev` branch.
- Keep each pull request focused on a single change. Unrelated fixes and
  refactors belong in separate pull requests.
- Fill in the pull request template.
- Title the pull request with one imperative sentence stating the outcome,
  with no prefix and under about 65 characters. Pull requests are
  squash-merged, so the title becomes the commit subject, and GitHub appends
  " (#N)" to it; the title carries no "(#N)" itself. For a single-commit pull
  request GitHub proposes the commit subject instead, so make the commit
  subject equal the title.
- Follow the code style: `ruff` and `mypy` enforce the mechanical rules
  (`make lint`), [`CODESTYLE.md`](CODESTYLE.md) carries the conventions the
  tooling cannot check. Run
  `git config blame.ignoreRevsFile .git-blame-ignore-revs` once so `git blame`
  skips the whole-repo reformat commit.
- Update documentation when behavior changes: the reference manual
  (`docs/reference_manual/`) for user-facing changes and docstrings for code changes.

### Changelog

`CHANGELOG.md` records what a deck author or a reader of the output would
notice: a DSL attribute, command, keyword, report property or plot added,
renamed, removed or changed in meaning; a change in simulation results; a
deck that used to run and now fails, or the reverse; the CLI and
installation requirements; and the report, plot, console and log output. It
also records bugs in any of these, including errors in the reference manual.
The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Nothing else gets an entry: no refactor, move, rename or removal inside
`navigate/`, and no change to what Python code can import. Typing, test,
lint, CI, `make` and tooling changes get none either, and neither does a
results-neutral change with no DSL or output effect. A pull request states
its user-visible effect in its description, so a reviewer can check the entry
against it.

An entry is one to three lines; related entries may share one bullet with a
sub-list, each item one to three lines. It states what the user sees and, for
a rename or removal, what to write instead, and it ends with the issue number
if there is one. It carries no "Breaking" label: Navigate does not keep
backwards compatibility, and a release may break old decks. How the change
works belongs in the pull request, not the changelog.

## Testing

All tests must pass before a pull request can be merged. Run the full suite
with `make test-all`, or the individual suites during development.

New code needs appropriate test coverage: `tests/AGENTS.md` says which suite
a check belongs in and points to each suite's conventions. The regression
baselines a change moves are regenerated only with `make regen-regression`
and committed as their own commit, with the baseline diff as review material
(`tests/regression/README.md`).

## Evidence in a pull request

The Evidence section of a pull request description shows what CI does not.
CI already reports the test suites, lint and the documentation build, so the
description never lists suites, their results or test counts. Naming what a
new test pins is fine.

- **Results unchanged.** The proof concerns what the model computes, not
  how the output presents it. Run every deck under `simulations/examples/`
  and `tutorials/` whose run reaches the changed code, on the base commit and
  on the branch. Report CSVs must be byte-identical, and xlsx reports
  identical cell by cell, since xlsx bytes differ between saves. For a deck
  that writes no report, pickle every node's profile and expectation after a
  full run on each side, and compare. Where the change deliberately alters an
  output's layout, format or wording, compare the values instead, and state
  the output change as a user-visible effect. Name the base commit and the
  decks run.
- The regression suite is not this proof: its baselines cover few decks and
  carry a noise floor (`tests/regression/README.md`).
- A change that touches nothing under `navigate/` or `assumptions/`, no deck
  or include, and no dependency in `pyproject.toml` needs no neutrality
  evidence and says nothing about it.
- **Results that move.** Give a table of the quantities and years that
  matter, base → branch, with the deck and the base commit, and explain each
  shift by the mechanism that causes it. Say that the regression baselines
  were regenerated with `make regen-regression` in a commit of their own,
  named by its subject.
- **Deck errors.** A new or changed deck error is shown by running the same
  deck through the CLI on base and branch: the command, the exit code and
  the trimmed message.
- **New checks.** A new test, lint rule or deck check gets a deliberate-break
  table: each break applied alone, and the failure it caused.
- **Not run.** End Evidence with a `Not run:` line naming any check a
  reviewer would expect that was skipped, and why. Never fill it by
  inference.

## Questions

Issues are the preferred way to ask. Whether you are unsure if a change needs
an issue first, want to discuss a design, or have a question about the
model, open an issue and we will get back to you.

## AI tools

The use of generative AI and related tools is neither encouraged nor
discouraged. You are responsible for the quality of your own contributions,
and we kindly ask that you do not clutter the repository with code or inputs
you do not fully understand. `AGENTS.md` at the repository root is the entry
point for anyone starting to work here; coding agents read it automatically.
The procedures for filing issues and writing pull requests are Agent Skills
in `.agents/skills/`.
