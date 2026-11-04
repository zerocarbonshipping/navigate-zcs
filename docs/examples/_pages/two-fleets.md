<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0

The source of docs/examples/two-fleets.ipynb, which is both the Examples page and
the Colab notebook. Edit this file, then run
    python docs/_figures/make_example_notebooks.py two-fleets
Each {{ name }} line becomes cells: see make_example_notebooks.py.
-->

{{ badge }}

# Two fleets in the Baltic

[Regional networks](regional-networks.md) · deck `simulations/examples/example_3/`

How much do the owners' efficiency choices matter on the same trade?

## The case

{{ map }}

- **Ships:** product tankers in the Baltic, in two fleets that are the same in
  everything but one choice. The *regular* owners fit no efficiency measure; the
  *efficient* owners can fit eight (air lubrication, rotor sails, hull paint,
  propeller devices and others). Each fleet starts with 2 MR tankers
  (~47,000 DWT) and 3 coastal tankers (~7,500 DWT): a handful of ships, not a
  market segment.
- **Routes:** the MR tankers sail Helsinki, Stockholm and Gdansk; the coastal
  tankers Helsinki, Tallinn and Stockholm. Trade grows 5 % a year.
- **Fuels:** fuel oil everywhere; e-ammonia from a European plant, bunkered at
  Helsinki and Stockholm only.
- **Policy:** EU ETS and FuelEU on every port, CII, and a net-zero framework
  whose values are the deck's own, not the data library's.
- **Horizon:** 2026 to 2050, yearly.

## Results

{{ setup }}

{{ run }}

{{ levers }}

## The deck

{{ deck }}

## Build it with an AI assistant

The prompt below rebuilds this deck exactly: an assistant that saw only the
prompt reproduced its results to the tonne. The deck's own numbers are in it as
the person's numbers, marked GIVEN, so they are not a source.
[Session 5](../workshop/05-build-your-own-case.ipynb) shows how to use it.

{{ prompt baltic-tankers: Full prompt for this case }}

The same question on one trade of your choice, with library numbers, is the
variant *Two fleets, one market* of the [trade route from Chile to
Rotterdam](trade-route.md).

## Run it yourself

In Colab: the badge at the top of this page opens it as a notebook, which runs
the deck and lets you move the levers. Nothing to install.

On your machine, install Navigate first: follow the [installation steps in the README](https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation),
or the more detailed [Getting started](../tutorials/getting_started.md) tutorial.
Then run the deck from the repository root:

```bash
python -m navigate simulations/examples/example_3/example_3.nav -d ./assumptions
```

To make a case of your own, copy the folder to `simulations/user/` and change
it, or have an AI assistant build one from the prompt above, as
[Session 5](../workshop/05-build-your-own-case.ipynb) shows.
