<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Workshop

The aim of this workshop is to work through practical cases with the Navigate model to get a sense of:

- how to create a model
- what type of data are used in the model and how they are organised
- how the model works and how inputs shape the results
- how the model can be used in practice

## What you'll do

1. **Get introduced and set up**: sanity-check your environment with a tiny, fast-running deck ([Session 1](01-setup-and-quicktest.ipynb))
2. **Understand the model logic**, with a simple case ([Session 2](02-vessel-case-study.ipynb))
3. **Build your own case with an AI assistant**: example prompts that turn a description of your case into a working model ([Session 3](03-build-your-own-case.ipynb))
4. **Run our reference scenarios**: pre-made assumptions set and models maintained by the Center ([Session 4](04-run-a-reference-scenario.ipynb))
5. **Simple sensitivity analysis**: pick one of four reference
   cases, move some of the assumptions behind it (fuel
   prices, regulatory stringency,...) and see how results change ([Session 5](05-build-your-own-whatif.ipynb))

To understand the details behind Navigate you can also check our [Tutorials](../tutorials/index.md) and
[Reference Manual](../reference_manual/index.md).

## How to run the workshop material

### Option 1 (recommended): Google Colab, nothing to install

Every session here except [Session 3](03-build-your-own-case.ipynb) opens with an **Open in Colab** badge. Click it and the notebook runs in your browser: no installation, nothing on your laptop. You need a free Google account to use it.

For Session 3 you will need to install Navigate on your own machine.

Note for Colab: a session is discarded after a period of
inactivity. If cells suddenly start failing on imports or missing files,
re-run the cells at the top.

### Option 2: locally, no Google account needed

If you would rather not use Google Colab, run the notebooks on your own machine with Jupyter. You need **Python 3.12 or newer** installed.

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
