<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Workshop

The aim of this workshop is to work through practical cases with the Navigate
model, so that you get a sense of:

- how the model works;
- how its input data are organised, and how those inputs shape the results;
- how the model can be used in practice, for example to analyse how a
  regulatory proposal may change shipping's decarbonisation pathways.

The workshop works from guided use of the model rather than from theory.
It starts with one simple case that is used to understand the model logic
([notebook 2](02-vessel-case-study.ipynb)), hands you prompts for building a simple
case of your own ([notebook 3](03-build-your-own-case.ipynb)), shows you some of the
Center's reference scenarios ([notebook 4](04-run-a-reference-scenario.ipynb)), and
ends with you moving the assumptions behind them and re-solving
([notebook 5](05-build-your-own-whatif.ipynb)).

To understand how Navigate itself is built in detail,
node by node, follow the [Tutorials](../tutorials/index.md) and check our
[Reference Manual](../reference_manual/index.md).

## What you'll do

1. **Get introduced and set up**: sanity-check your environment with a tiny,
   fast-running deck.
2. **Work one trade end to end**, a fleet of Panamax bulk carriers hauling
   copper from Chile to Rotterdam: build the deck, see how its input data is
   organised, watch Navigate take one time step decision by decision, read
   twenty-five years of results, then run some sensitivities.
3. **Have an assistant build a case for you**: prompts that turn a description of
   a fleet and a trade into a working deck, and how to run what comes back.
4. **Run the reference scenarios** end to end, read Navigate's own output plots
   and the assumptions workbook a run exports, and compare three levels of
   regulatory stringency to see how each one changes the transition pathway.
5. **Change the numbers yourself, at global scale**: pick one of four reference
   decks, one per regulatory world, move the assumptions behind it — fuel
   prices, carbon price, regulatory stringency, how much green fuel can be made
   — and put your version beside the original, the same way
   [notebook 2](02-vessel-case-study.ipynb) does it but on the whole world
   fleet.

## How to run the workshop material

### Option 1 (recommended): Google Colab, nothing to install

Every notebook here except [notebook 3](03-build-your-own-case.ipynb) opens with an
**Open in Colab** badge.
Click it and the notebook runs in your browser on Google's machines: no Python,
no installation, nothing on your laptop. You need a free Google account. The
notebook clones this repository and installs Navigate for you as its first
step. Notebook 3 is the exception because it has an assistant write a deck into
this repository, which needs Navigate on your own machine.

One Colab habit is worth knowing: a session is discarded after a period of
inactivity. If cells suddenly start failing on imports or missing files,
re-run the cells at the top.

### Option 2: locally, no Google account needed

If you would rather not use Google Colab, run the notebooks on your own machine
with Jupyter. You need **Python 3.12 or newer**.

To open a terminal: on **Windows** press Start and type `PowerShell`, then
Enter; on **macOS** press Cmd+Space and type `Terminal`; on **Linux** press
Ctrl+Alt+T. Then run these commands, one at a time:

```bash
git clone -b dev-workshop https://github.com/zerocarbonshipping/navigate-zcs.git
cd navigate-zcs
pip install .
pip install jupyterlab
jupyter lab
```

The last command opens Jupyter in your browser. From there, open
`docs/workshop/` and start with the first notebook. No Google account is
involved at any point.

If `pip install .` fails, the main
[README](https://github.com/zerocarbonshipping/navigate-zcs#installation)
covers installation, including the two errors that commonly come up on
Windows: a blocked PowerShell script, and an `Access is denied` from
`pip.exe`.

## Disclaimer

Navigate is an open-source analytical model for research and scenario
analysis. Outputs depend on the assumptions selected and should not be
interpreted as forecasts, benchmarks, recommendations, or investment advice.

```{toctree}
:titlesonly:

01-setup-and-quicktest
02-vessel-case-study
03-build-your-own-case
04-run-a-reference-scenario
05-build-your-own-whatif
references
```
