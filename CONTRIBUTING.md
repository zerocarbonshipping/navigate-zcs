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
refactors, should start as a feature request issue. This lets us align on
scope and design before you invest significant effort. Smaller features can
be submitted directly as a pull request.

**Assumption changes** must include references or a justification for the new
values, so that the provenance of the model inputs stays traceable.

## Pull request expectations

- Target the `dev` branch.
- Keep each pull request focused on a single change. Unrelated fixes and
  refactors belong in separate pull requests.
- Write a clear description: what the change does, why it is needed, and how
  it was verified.
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
results-neutral change with no DSL or output effect. A pull request without
an entry says so in its description.

An entry is one to three lines; related entries may share one bullet with a
sub-list, each item one to three lines. It states what the user sees and, for
a rename or removal, what to write instead, and it ends with the issue number
if there is one. It carries no "Breaking" label: Navigate does not keep
backwards compatibility, and a release may break old decks. How the change
works belongs in the pull request, not the changelog.

## Testing

All tests must pass before a pull request can be merged. Run the full suite
with `make test-all`, or the individual suites during development.

New code needs appropriate test coverage. `tests/README.md` is the short
guide to when a change needs a test and where it goes; `tests/AGENTS.md`
says which suite a check belongs in and points to each suite's conventions. Changes that alter
simulation results should explain the difference in the pull request
description; the regression baselines they move are regenerated only with
`make regen-regression` and committed as their own commit, with the baseline
diff as review material (`tests/regression/README.md`).

## Questions

Issues are the preferred way to ask. Whether you are unsure if a change needs
a feature request first, want to discuss a design, or have a question about
the model, open an issue and we will get back to you.

## AI tools

The use of generative AI and related tools is neither encouraged nor
discouraged. You are responsible for the quality of your own contributions,
and we kindly ask that you do not clutter the repository with code or inputs
you do not fully understand. `AGENTS.md` at the repository root is the entry
point for anyone starting to work here; coding agents read it automatically.
