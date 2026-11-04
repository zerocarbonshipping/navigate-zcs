<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0

The source of docs/examples/south-pacific.ipynb, which is both the Examples page
and the Colab notebook. Edit this file, then run
    python docs/_figures/make_example_notebooks.py south-pacific
Each {{ name }} line becomes cells: see make_example_notebooks.py.
-->

{{ badge }}

# Island trade in the South Pacific

[Regional networks](regional-networks.md) · deck `simulations/examples/example_2/`

Can a regional bulk trade switch to biodiesel when only its main ports supply it?

## The case

{{ map }}

- **Ships:** 6 Handysize bulk carriers (~26,000 DWT), all on fuel oil, the same
  design throughout: the oil engine can burn biodiesel (FAME) instead. The
  owners can fit seven efficiency measures.
- **Route:** regional trips between Australia, New Zealand, Fiji, Samoa and Tonga,
  with no fixed order of calls. Trade grows 5 % a year.
- **Fuels:** fuel oil at every port; FAME made from used cooking oil in Europe,
  shipped 11,000 to 12,200 nm, and bunkered in Australia and New Zealand only.
- **Policy:** CII and a net-zero framework on every port, the framework with
  values that are the deck's own, not the data library's. No EU policy.
- **Horizon:** 2026 to 2050, yearly.

## Results

{{ setup }}

{{ run }}

{{ levers }}

## The deck

{{ deck }}

## Build it with an AI assistant

The prompt below rebuilds this deck exactly: an assistant that saw only the
prompt reproduced its results. The deck's own numbers are in it as the person's
numbers, marked GIVEN, so they are not a source. Ships on trips between several
ports in no fixed order, some ports without the new fuel, start from it.
[Session 5](../workshop/05-build-your-own-case.ipynb) shows how to use it.

{{ prompt south-pacific: Full prompt for this case }}

## Run it yourself

In Colab: the badge at the top of this page opens it as a notebook, which runs
the deck and lets you move the levers. Nothing to install.

On your machine, install Navigate first: follow the [installation steps in the README](https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation),
or the more detailed [Getting started](../tutorials/getting_started.md) tutorial.
Then run the deck from the repository root:

```bash
python -m navigate simulations/examples/example_2/example_2.nav -d ./assumptions
```

To make a case of your own, copy the folder to `simulations/user/` and change
it, or have an AI assistant build one from the prompt above, as
[Session 5](../workshop/05-build-your-own-case.ipynb) shows.
