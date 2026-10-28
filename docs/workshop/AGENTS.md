<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Editing the workshop

This file is for anyone changing the workshop in `docs/workshop/`, human or coding
agent. It states the conventions the notebooks follow and the checks a change
needs. It does not explain Navigate: the notebooks do that. For building a deck
from one of Session 5's prompts, see `building-a-deck.md`.

## What is here

Five sessions, each a notebook, in this order:

1. `01-run-a-simple-case.ipynb`: one case, run and varied
2. `02-run-a-global-case.ipynb`: the reference scenarios, on a coarse time grid
   with levers, then three of them year by year (25-50 minutes)
3. `03-how-a-navigate-model-is-built.ipynb`: Session 1's case, its deck and its data
4. `04-how-navigate-solves.ipynb`: the same case, solved step by step
5. `05-build-your-own-case.ipynb`: building a case with an AI assistant, step by step
   (local install only)

`_style.py` holds the shared figure style. `index.md` is the overview page. The
decks the sessions run are in `simulations/examples/example_4/` and
`simulations/scenarios/workshop_whatif/`; the maps and schematics are drawn by the
scripts in `docs/_figures/`.

## Branch

The workshop is built on `main`, the released Navigate that participants install,
not on `dev`. Do not merge `dev` into the workshop branch: its API changes break
the decks and the notebooks. The workshop is never merged into or deployed from
`main`.

Every link to the workshop points at the `dev-workshop` branch, because no workshop
page exists on the published site: the Open in Colab badges, `BRANCH` in each
Setup cell, the links between notebooks, and the clone command in `index.md`.
When the workshop moves to another branch, change all of them together
(`grep blob/dev-workshop`); one left behind keeps working until the old branch is
deleted.

## Navigate's code

Work on the workshop does not change Navigate's core code, `navigate/`. When an
error turns up in it, do not fix it there: describe it to the workshop authors,
with the file and line, what goes wrong and the change you would suggest, so it
can be filed as an issue against Navigate. A notebook may work around a model
behaviour at run time, as `navigate_charts()` swaps colours while Navigate draws,
but never by patching the package. A change to `navigate/` is made only when the
authors ask for that specific change, and then as a commit of its own.

## Prose

- Name the actor. The **owners** order, retrofit and scrap ships and fit
  efficiency technology; the **operators** choose speed and bunkering. "The fleet"
  is not an actor: write the owners, the operators, or both, and "the ships" for
  the hulls. `Fleet` as the deck node keeps its name.
- When restructuring, move paragraphs as they are. Corrections are limited to
  spelling and grammar, which are fixed as soon as they are noticed. A factual
  problem in existing prose is raised with the authors, not rewritten in place.
- Teaching belongs in the notebook. Comments in `.nav` and `.inc` files stay
  minimal: the SPDX header, a one-line title, the INVENTED marker and what a
  number was derived from, and syntax traps the code cannot show.
- Before changing a number in the prose to match a run, run again and check it is
  stable. The global decks move in the last digit from one run to the next, so
  quote them to no more precision than they reproduce at. The example_4 figures
  reproduce exactly.

## Numbers

Every assumption comes from `assumptions/`, referenced by name. The example decks
teach structure, never numbers: some of their values exist nowhere in the library.
A number the library lacks is marked INVENTED, with what it was derived from, and
listed in the `.nav` header.

## Figures

- Colours come from `PALETTE` in `_style.py`, through `swatch(hue, level)`, never
  as a raw hex. Use levels 1 to 8: level 0 does not show on a projector. The
  scripts in `docs/_figures/` use the same colours. Every figure the workshop
  shows follows this palette, results of a Navigate run included. Navigate's own
  charts use the library's older palette, so draw them again with
  `navigate_charts()` in `_style.py`, which re-renders a run's charts from its
  `plot_data.pkl` in this palette, rather than displaying the `.png` files.
- Show a result with a figure the workshop already draws, so the reader can
  compare it with the others. Factor the plotting code into a function rather than
  adding a chart; propose a new type of figure only when none fits.

## Notebooks

- Keep each cell's `source` a list of lines, which is what keeps a notebook diff
  readable. `nbformat.read` joins them into one string and `nbformat.writes`
  splits them again, so write with `nbformat.writes`, never a raw `json.dumps` of
  an nbformat object.
- Keep each file's own line ending (detect it from the raw bytes; it is not the
  same in every notebook) rather than forcing one.
- Execute with `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` set before the kernel
  starts, or Navigate's banner is saved as mojibake. Save the kernelspec as the
  standard `python3`.
- Before committing, check: the notebook validates, no output is an error, no
  output contains mojibake (`â€`, `Ã`), and no output contains a local path or
  user name.
- The docs build does not execute the notebooks (`nb_execution_mode = 'off'`), so
  what is saved is what is published.

## Prompts

Session 5 teaches the process in seven steps, worked on Session 1's case, and
shows a global and a regional case as cards. `prompt-bank.md`, not on the site,
holds every full prompt and every variant, grouped by family, so that assistants
start from the closest one. The start-up prompt has the assistant propose the
family and the model, show a one-page case sheet for approval, and build from
the case sheet and the model's full prompt. This process was chosen on
2026-10-28 over writing a full prompt for approval: in six cold builds it was as
accurate, with a third of the text to approve.

The bank grows from contributions. A participant's assistant ends its report with
a prompt bank entry (building-a-deck.md says what it holds), which the participant
pastes into an issue. Add it as a variant of its model by default, and as a full
entry only when it needs a structure or a fix that no entry has; fold its notes
into building-a-deck.md; promote a variant that several people build to a full
entry. A report that says "none close" marks a family or a template the bank
lacks.

Avoid wording that asks a model about its own prompt or reasoning ("the prompt
you would want to be given"): it tripped a model's safety filter in testing.

The start-up prompt and the bank's full prompts are tested as a chain, cold, by
an assistant that sees only the prompt text:

1. the start-up prompt, carried through to a build, on a new case of each family;
2. each full prompt, run directly; a variant, built from its model.

A template that rebuilds a deck already in the repository (the copper trade is
`example_4`, Session 2's is in `simulations/scenarios/`) tells the assistant it
may use that deck. To test that the prompt alone is enough, the tester's own
instructions forbid opening it; the prompt itself does not.

Check that every instruction of the start-up prompt (the family and model
before the questions, the case sheet, the new folder and its `_2`, no change to
existing files, INVENTED marking, the prompt bank entry) is obeyed by the build.
Keep the start-up prompt as short as a participant could write it, and shorten
it only with a chain test showing the cut breaks nothing. The rules Session 5's prompts share live in
`building-a-deck.md`: change them there, not in each prompt, and test the chain
again afterwards.

## Running decks

From the repository root, `python -m navigate <deck>.nav -d ./assumptions`
(`-s` skips the plots). The shorter `navigate` command may run another installed
copy of Navigate. Do not install or upgrade packages into an environment you did
not create.

## Improving this file

A convention that a review had to correct, or a check that would have caught a
problem, belongs here. Add it in the section it concerns, in a sentence, with the
reason when the reason is not obvious.
