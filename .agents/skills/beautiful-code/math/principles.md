<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Mathematical code

Mathematical code minimizes the mental effort required by a subject matter expert in
understanding its intent by using the standard mathematical notation and conventions.

These principles add to the general ones in `../SKILL.md`.

## 1. Use mathematical notation

Name variables as the field's standard notation names them, so the code reads like the
formula a subject matter expert already knows: `A`, `b`, `x` and `r` for a linear
system and its residuals, not `system_matrix`, `rhs`, `variables` and `residuals`. The
reader of mathematical code is that expert, and a descriptive name makes them translate
back into the notation they think in. Within this domain this wins over the general
preference for descriptive names. Where the project's linter or style forbids such
names, such as uppercase locals, the project wins.

## 2. Keep plumbing out of the mathematics

Indexing, iteration bookkeeping and long attribute paths are plumbing: the code needs
them, but they are not part of the mathematical method. Mixed in with the mathematics,
they make the reader track two things at once, and they stretch lines until calls wrap.
Put them behind an iterator or accessor that yields the objects the mathematics works
on, and bind the quantities the body uses repeatedly to short local names, so the body
reads as the method itself. A short name follows section 1 where the field has a
notation for the quantity, such as `dt` for a time step; otherwise it is a shortening
the reader can trace back to its source at a glance.

## 3. Simplify before you compute

Where intermediate quantities cancel, compute the reduced expression, unless the
intermediate is a quantity the reader needs by name. A quantity that cancels still tells
the expert the result depends on it, and dividing by it can fail where the result is
well defined.
