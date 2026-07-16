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
- Follow the existing code style (`flake8` configuration and
  [`CODESTYLE.md`](CODESTYLE.md)). Match the conventions of the file you are
  editing.
- Update documentation when behavior changes: the reference manual
  (`docs/reference_manual/`) for user-facing changes and docstrings for code changes.
- Add an entry to `CHANGELOG.md` for user-visible changes. See the
  [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## Testing

All tests must pass before a pull request can be merged. Run the full suite
with `make test-all`, or the individual suites during development:

New code needs appropriate test coverage:

- New node attributes must be covered by the attribute tests
  (`tests/attribute`).
- New non-trivial calculations need a unit test (`tests/unit`).
- Changes that alter simulation results should explain the difference in the
  pull request description.

## Questions

Issues are the preferred way to ask. Whether you are unsure if a change needs
a feature request first, want to discuss a design, or have a question about
the model, open an issue and we will get back to you.


### Note on AI Tools

The use of Generative AI and related tools is neither encouraged nor discouraged. However, you are responsible for the quality of your own contributions, and we kindly ask that you do not clutter the repository with code or inputs you do not fully understand.