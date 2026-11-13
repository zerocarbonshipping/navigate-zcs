---
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
name: beautiful-code
description: The maintainers' taste in readable code - five principles with calibrated examples, plus domain layers such as mathematics. Use whenever you write, refactor or review code in any language.
---

# Beautiful code

Beautiful code minimizes the mental effort required to understand its intent, structure,
and behavior.

This is the maintainers' taste, not a style guide. The project's own code style and
conventions, and the generally acknowledged guidelines for the language, such as PEP 8
or the C++ Core Guidelines, come first; this skill applies in the room they leave.

The examples are in Python, but the principles hold for any language. They leave out
type hints and docstrings because the project's code style governs those; their absence
is not a preference. They are illustrative: operators carry their mathematical or
conventional meaning, not the semantics of a particular library.

## Principles

1. **Visual flow.** Does the eye move through the code naturally? Split a body into
   blank-line-separated blocks, one step each, grouped by the steps' primary purpose,
   with setup before the steps that use it. Keep lines within a block of similar length,
   so the eye scans down rather than across. Make names descriptive without being
   exhaustive: the definition holds the detail. A line that wraps is a symptom: drop
   what the context already says, bind a receiver used repeatedly to a local, bind an
   argument to a local before the call that takes it, call the variables `key, value` in
   a loop that only passes a mapping's entries on, write a collection as one literal,
   write a comprehension that does not fit on one line as a loop, or split the
   expression into named steps. A loop that calculates with its entries keeps
   descriptive names, since the arithmetic reads through them. An abbreviation the
   reader cannot trace at a glance, or a module-level alias, hides the wrap but moves
   the cost to the reader.
2. **Local comprehensibility.** Can I understand this piece without constantly looking
   elsewhere? Let what a piece depends on and what it changes show where it is used, in
   its arguments and its return value, rather than in state set or changed far away.
3. **Clarity of intent.** Does the code communicate what it means, rather than merely
   what it does? Name a concept, as a predicate, constant or function, where the reader
   would otherwise have to work it out from the mechanics.
4. **Structural consistency.** Do similar concepts use similar shapes, names and
   patterns? Generic verb prefixes such as calculate, compute, update, assign and define
   must have one intent throughout the repository: for example, "calculate" always
   returns something after a calculation, and "update" always works in place. Which
   meaning a verb gets matters less than that it never varies. Look for the repository's
   existing convention and follow it; where there is none, pick one and apply it
   throughout the code you write. Bringing existing code outside your change into line
   is a separate task, since renames there widen the diff beyond what was asked.
5. **Information density.** Does every line communicate something useful without
   becoming compressed or cryptic? Drop lines that only restate the obvious or a
   guarantee enforced elsewhere, and values nobody reads, such as a default that is
   always overwritten or a field no caller uses. Split expressions that make the reader
   hold several steps at once.

The principles can pull against each other, density against flow for instance. Aim for
the least total effort for the reader.

## Examples

Read `examples.md` before you write or review code. Each examples file, a domain
layer's included, has a section per principle, holding groups of examples on one topic.
Each group shows the topic in up to four kinds:

- **Beautiful:** code to imitate as it stands, the principle done well with nothing
  traded away.
- **Ugly but correct:** code that works and would pass a review for correctness, but
  costs the reader effort it need not.
- **Preferred over a reasonable alternative:** two versions that both work and that a
  careful programmer might write; the maintainers prefer the first.
- **Borderline:** no firm preference; each version is acceptable and the entry lists
  what tips the balance each way. Weigh those considerations rather than picking a
  side. Where a case of your own is this close, follow the surrounding code.

Each example says concretely what makes one version better; carry those reasons over to
your own code, not the surface of the example.

## Domains

A domain layer adds principles and examples for code of one kind. Read it only when the
code belongs to that domain, after this file. The project's conventions still come
first; in the room they leave, a layer's principles win over the general ones where they
conflict.

- `math/`: code that implements mathematical or numerical methods, such as linear
  algebra, optimisation, statistics or numerical simulation. Read `math/principles.md`
  and `math/examples.md`.
