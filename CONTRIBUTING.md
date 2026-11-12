<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Contributing to Navigate

Thank you for your interest in improving Navigate. In principle anything can
be contributed: bug fixes, features, new policies, assumptions, documentation,
and tutorials. Contributions arrive as pull requests, from a fork or, for the
maintainers, from a branch of the repository itself.

## Getting started

1. Fork the repository and clone your fork.
2. Set up a development environment as the README says under "For
   development".
3. Create a branch from `dev` for your change.
4. Verify your setup with `make check`, which runs the linters and the unit
   suite.
5. Skim [ARCHITECTURE.md](ARCHITECTURE.md) for the package map and the
   data-flow invariants contributions must respect.

## What to contribute

Any valuable contribution is welcome.

**Bug fixes** can be submitted directly as a pull request. Describe the bug
and how the fix addresses it. If you have found a bug but do not plan to fix
it yourself, please open an issue instead.

**Changes to what the model represents**, such as a new policy, node type or
mechanism, should start as an issue. This lets us align on scope and design
before you invest significant effort. Smaller features can be submitted
directly as a pull request, and so can a rework of existing code that your
change needs; a rework beyond what it needs gets an issue of its own.

**Assumption changes** must include references or a justification for the new
values, so that the provenance of the model inputs stays traceable.

## Pull request expectations

- Target `dev`, or the integration branch of the larger effort the change
  belongs to; never `main`, the release branch.
- Keep each pull request one reviewable change: the rework the change needs
  belongs in it, unrelated fixes and refactors in pull requests of their own.
- Fill in the pull request template.
- Title the pull request with one imperative sentence stating the outcome:
  no prefix, no "(#N)", under about 65 characters. The squash merge makes it
  the commit subject and appends " (#N)". For a single-commit pull request
  GitHub proposes the commit subject instead, so make the two equal.
- Follow the code style: `ruff` and `mypy` enforce the mechanical rules
  (`make lint`), [`CODESTYLE.md`](CODESTYLE.md) carries the conventions the
  tooling cannot check.
- Update documentation when behavior changes: the reference manual
  (`docs/reference_manual/`) for user-facing changes and docstrings for code changes.

### Changelog

`CHANGELOG.md` records what a deck author or a reader of the output would
notice: a DSL attribute, command, keyword or result added, renamed, removed or
changed in meaning; a change in simulation results beyond rounding (see
Testing); a deck that used to run and now fails, or the reverse; the CLI and
installation requirements; and the results file, console and log output, error
messages a deck author sees included. It also records bugs in any of these,
including errors in the reference manual. The format is Keep a Changelog, in
the version the head of `CHANGELOG.md` cites.

Nothing else gets an entry: no refactor, move, rename or removal inside
`navigate/`, and no change to what Python code can import. Typing, test,
lint, CI, `make` and tooling changes get none either, and neither does a
results-neutral change with no DSL or output effect. A pull request states
its user-visible effect in its description.

An entry is one to three lines; related entries may share one bullet with a
sub-list, each item one to three lines. It states what the user sees and, for
a rename or removal, what to write instead, and it ends with the issue number
if there is one. It goes under one of Keep a Changelog's headings and carries
no "Breaking" label or heading: Navigate does not keep backwards
compatibility, and a release may break old decks. How the change
works belongs in the pull request, not the changelog.

## Testing

All tests must pass before a pull request can be merged. Run the full suite
with `make test-all`, or the individual suites during development.

The suite is kept small on purpose, so new code does not by default get a
test: `tests/AGENTS.md` says when a change earns one and which suite it
belongs in, and that coding agents propose tests rather than write them.

Changes that alter simulation results should explain the difference in the
pull request description. A pull request that changes code or assumptions and
should not alter them carries the `maintenance` label; CI then runs a fixed set
of decks on the pull request merged into its base and on that base, and fails
on any difference beyond rounding, the tolerance the `writing-pull-requests`
skill names. Run the same
comparison locally against the newest `dev` with `make compare-results`.

## Questions

Issues are the preferred way to ask. Whether you are unsure if a change needs
an issue first, want to discuss a design, or have a question about the
model, open an issue and we will get back to you.

## AI tools

The maintainers develop Navigate with coding agents, which work from the same
documents as everyone else: `AGENTS.md` at the root, the `AGENTS.md` files in
`tests/`, `docs/` and `assumptions/`, and the Agent Skills for issues and pull
requests in `.agents/skills/`. Whether you use such tools is your choice; either
way you answer for what you submit, so please do not add code or inputs you do
not fully understand.

Do not add a `CLAUDE.md` or `CLAUDE.local.md`: where either exists, Claude Code
stops reading the `AGENTS.md` files.
