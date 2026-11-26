<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Leadership demo: Navigate, Horizon and Lantern

A Colab notebook that shows the three tools on the Center's reference scenario of
the world fleet, for a presenter to run in about ten minutes. It lives on the
branch `leadership-demo` only and is never merged.

[Open it in Colab](https://colab.research.google.com/github/zerocarbonshipping/navigate-zcs/blob/leadership-demo/demo/leadership/leadership_demo.ipynb)

## Presenting it

1. About five minutes before the meeting, open the notebook in Colab (Chrome
   works best for Lantern's tab) and run **Setup**: about two minutes.
2. In the meeting, run the cells one by one as you talk. The notebook opens
   with the outputs of an earlier run, so a cell that is not run still shows
   its chart.
3. **Solve the scenarios** solves mid regulation live, about a minute on
   Colab; the other two come from `results/`. Pick `all three` to solve them
   side by side (two to three minutes) or `none` to skip the wait.
4. **Load the study** takes the hundred futures from `results/`; tick
   `RUN_STUDY_LIVE` to run six here instead (about three minutes).
5. **How often the fleet gets there** counts the futures that reach a cut in
   emissions; move its slider and run the cell again to try another cut.
6. **Open Lantern** starts Lantern's viewer in the notebook and opens it in a
   new tab. If the browser blocks Colab's tab, the link beside the button shows
   the viewer in the notebook.

## What is here

| File | What |
|---|---|
| `leadership_demo.ipynb` | the notebook, with the outputs of one run |
| `build_notebook.py` | writes the notebook's cells; edit the text there, not in the notebook |
| `showcase.py` | the notebook's cards and charts, and the solve and Lantern helpers |
| `overlay/` | laid over notebook 2's `global_case`: the study `demo.hor`, and `plots.yaml`, Lantern's catalogue at the pinned commit with the demo's runs named and its `headline` plots |
| `results/` | the three scenarios on the coarse grid and the hundred-future study, from `bake.py` |
| `images/` | the banner and the toolchain diagram, as SVG and the PNGs `make_images.py` draws |

The case is `docs/notebooks/notebook_2/global_case` as the branch has it; the
study varies eight of notebook 2's levers over its suggested spans.

## Refreshing

From the repository root, with Navigate, Horizon and Lantern installed in
`.venv` (Horizon and Lantern at the commits the setup cell pins):

```bash
.venv/bin/python demo/leadership/bake.py /tmp/demo-bake   # about 30 minutes on 14 cores
python demo/leadership/make_images.py                     # needs cairosvg and Aktiv Grotesk
python demo/leadership/build_notebook.py
```

Then execute the notebook from a fresh kernel with `ROOT` set to a folder of
your own and the branch cloned into `ROOT/navigate-zcs`, set `ROOT` back to
`/content`, and commit it with its outputs.
