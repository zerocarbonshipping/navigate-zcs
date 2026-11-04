<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0

The source of docs/examples/mainline-and-feeders.ipynb, which is both the Examples
page and the Colab notebook. Edit this file, then run
    python docs/_figures/make_example_notebooks.py mainline-and-feeders
Each {{ name }} line becomes cells: see make_example_notebooks.py.
-->

{{ badge }}

# A mainline and its feeders

[Regional networks](regional-networks.md) · deck `simulations/examples/example_1/`

How do two ship sizes on connected routes choose fuels when the ports supply them
unevenly?

## The case

{{ map }}

- **Ships:** two fleets on two routes. 5 mainline container ships
  (~15,000 TEU), four in five on fuel oil, the rest on methanol; 50 feeders
  (~1,500 TEU), almost all on fuel oil. Both can order or convert to methanol
  ships.
- **Routes:** the mainline sails Singapore to Rotterdam, 8,300 nm each way in the
  deck, laden west and nearly empty east; the feeders sail Rotterdam, Hamburg
  and Aalborg.
- **Fuels:** fuel oil at every port; bio-methanol from a European plant, at
  every port but Aalborg.
- **Policy:** EU ETS and FuelEU on the three European ports; CII and a net-zero
  framework on all four, the framework with values that are the deck's own, not
  the data library's.
- **Horizon:** 2026 to 2050, yearly.
- **Freight rate:** container ships carry TEU, so the freight rate here is per
  thousand TEU-miles: do not compare it with the bulk carriers'.

## Results

{{ setup }}

{{ run }}

{{ levers }}

## The deck

{{ deck }}

## Build it with an AI assistant

The prompt below rebuilds this deck exactly: an assistant that saw only the
prompt reproduced its results to the tonne. The deck's own numbers are in it as
the person's numbers, marked GIVEN, so they are not a source. A network of
connected routes starts from it. [Session 5](../workshop/05-build-your-own-case.ipynb)
shows how to use it.

{{ prompt mainline-feeders: Full prompt for this case }}

## Run it yourself

In Colab: the badge at the top of this page opens it as a notebook, which runs
the deck and lets you move the levers. Nothing to install.

On your machine, install Navigate first: follow the [installation steps in the README](https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation),
or the more detailed [Getting started](../tutorials/getting_started.md) tutorial.
Then run the deck from the repository root:

```bash
python -m navigate simulations/examples/example_1/example_1.nav -d ./assumptions
```

To make a case of your own, copy the folder to `simulations/user/` and change
it, or have an AI assistant build one from the prompt above, as
[Session 5](../workshop/05-build-your-own-case.ipynb) shows.
