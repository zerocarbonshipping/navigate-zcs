<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a documentation issue

- **Quote the wrong or missing text**, with its page and heading, and name
  the source of truth it disagrees with: the setter and its docstring, the
  parser table (`navigate/parser/_attributes.py`, `_commands.py`), or the
  code path. Give both sides.
- **When it is unclear which side is wrong**, say so. If the code turns out
  to be wrong, the issue is a bug.
- Several mismatches of one kind, found in one pass, make one issue.
- **Location** names the documentation file and the source file it was
  checked against.
- The reference manual describes behaviour as users see it, with no
  modelling derivations. Codebase internals belong in the root files and the
  folder READMEs (`AGENTS.md`), so an issue about them names those files,
  not the manual.
