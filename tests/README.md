<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Writing tests for Navigate

A test is a tripwire for a decision. Write one when your change decides
something (a rule, a unit, an error message, how the model responds to an
input) that someone could break tomorrow without noticing.

## Three questions before writing a test

1. What did I decide? If you cannot say it in one sentence, you probably do
   not need a test.
2. Would anything fail today if someone broke it? If something would, you are
   done.
3. Do I know the right answer without running the code? Work it out by hand,
   from the documentation or from domain reasoning. Never copy the current
   output into the test.

## Where it goes

| I… | Then… |
|---|---|
| wrote a calculation or a rule | a unit test with a hand-derived expected value, in `tests/unit` |
| added a DSL attribute or command | use it in the attribute coverage deck; `tests/attribute` fails until it is there |
| changed how the model responds | keep `tests/behaviour` green, add a pair if the mechanism is new, and regenerate the regression baselines in a commit of their own |
| fixed a bug | a test that fails without the fix, at the lowest level that reproduces it |
| refactored | no new test; if existing tests break beyond import paths, they test the code's structure rather than its behaviour |

## What not to test

- numpy, scipy or Python itself;
- a formula copied into the test;
- that a constructor stores its arguments, or that a valid input is accepted;
- the same rule once per caller: test it once, where it lives.

`AGENTS.md` in this folder has the full rules, which suite answers which
question, and how to run them.
