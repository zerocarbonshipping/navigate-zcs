<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0

The source of docs/examples/caribbean.ipynb, which is both the Examples page and
the Colab notebook. Edit this file, then run
    python docs/_figures/make_example_notebooks.py caribbean
Each {{ name }} line becomes cells: see make_example_notebooks.py.
-->

{{ badge }}

# Caribbean shipping under global and EU rules

[Regional networks](regional-networks.md) · deck `simulations/examples/example_5/`

How are a region's own ships affected by global and EU rules, today and if
extended to them?

## The case

{{ map }}

- **Ships:** 330 regional ships (144 tugs, 47 ferries, 85 general cargo ships
  and 54 small tankers), nearly all under 5,000 GT, and 40 container feeders of
  about 1,500 TEU. Fleet counts from the IMO CARES report (2024); the split of
  the cargo ships is INVENTED.
- **Routes:** the feeders on a Miami - Kingston - Trinidad - Martinique loop;
  the regional ships inside and between the three Caribbean ports.
- **Fuels:** blue and e-ammonia, e-methanol and bio-methanol, made in Trinidad,
  on the US Gulf Coast or in Chile and shipped in; LNG at Kingston and Miami only.
- **Policy:** one deck with today's rules (a global fuel standard, the EU ETS and
  FuelEU) on the feeders only. It is run three ways, which differ in whom the
  rules cover: nobody (no policy); the feeders (today's rules); the feeders and
  the regional ships (extended).
- **Horizon:** 2026 to 2050, yearly.

The regional fleet is not calibrated: with the library's world-average ships it
burns more fuel than CARES reports, so compare the runs with each other, not
with the region's real totals.

## Results

{{ setup }}

{{ run }}

{{ levers }}

## The deck

{{ deck }}

## Build it with an AI assistant

This deck was built from the prompt below by an assistant that saw only the
prompt. A new regional network starts from it, or from the case whose routes
look most like yours. [Session 5](../workshop/05-build-your-own-case.ipynb)
shows how to use it.

{{ prompt caribbean: Full prompt for this case }}

## Run it yourself

In Colab: the badge at the top of this page opens it as a notebook, which runs
the deck three ways and lets you move the levers. Nothing to install.

On your machine, install Navigate first: follow the [installation steps in the README](https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation),
or the more detailed [Getting started](../tutorials/getting_started.md) tutorial.
Then run the deck from the repository root:

```bash
python -m navigate simulations/examples/example_5/example_5.nav -d ./assumptions
```

To make a case of your own, copy the folder to `simulations/user/` and change
it, or have an AI assistant build one from the prompt above, as
[Session 5](../workshop/05-build-your-own-case.ipynb) shows.
