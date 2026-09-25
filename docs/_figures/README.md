# Workshop figure sources

Scripts and source data that generate figures for the workshop notebooks, plus
the small tool for editing those notebooks. This folder is **not** documentation
— it is excluded from the Sphinx build in `docs/conf.py`.

## The workshop maps

Two notebooks open with a map, and both travel the same way. The SVG in
`docs/_static/` is the **source of truth** in each case:

| map | SVG | notebook |
|---|---|---|
| `example_4` | `example_4_map.svg` (940x470) | `02-vessel-case-study.ipynb` |
| `reference_scenario` | `reference_scenario_map.svg` (940x376) | `04-run-a-reference-scenario.ipynb` |

Rasterise, then embed, from the repository root:

```bash
python docs/_figures/render_map_png.py                      # -> docs/_figures/example_4_map.png
python docs/_figures/map_to_notebook.py                     # -> notebook 2 cell 2, as base64 PNG

python docs/_figures/render_map_png.py reference_scenario   # -> docs/_figures/reference_scenario_map.png
python docs/_figures/map_to_notebook.py reference_scenario  # -> notebook 4 cell 2, as base64 PNG
```

Both default to `example_4`, so the original two-argument-free invocations still
mean what they did. `map_to_notebook.py` also takes `--dry-run`, which reports
the cell it would rewrite and writes nothing.

Only the example_4 map has a generator for its SVG:

```bash
python docs/_figures/make_example_4_map.py   # -> docs/_static/example_4_map.svg
```

`reference_scenario_map.svg` is hand-maintained: edit the file and re-run the
two steps above. Its wording is checked against the deck, so re-read
`simulations/scenarios/` before changing a number or a claim on it — the
pathway counts, the 2050 electricity costs and the jurisdictions on that map
are all readable off a solved scenario.

The notebook cannot carry the SVG: Jupyter and Colab both strip SVG and HTML
from untrusted notebooks until the cell is run, and the map is a markdown cell
precisely so that nothing has to be run. A base64 PNG in markdown is exempt from
that, and renders in Colab, JupyterLab, the Sphinx site and GitHub's preview
alike.

### Two things the scripts read from the file rather than assume

Both were constants once, and both are wrong for one of the two maps:

- **The raster size is the SVG's own `viewBox`.** The maps are different heights,
  and a hardcoded size silently rescales or crops one of them.
- **The line ending is whichever the notebook already uses.** Notebook 2 is CRLF
  on disk and notebook 4 is LF. `Path.write_text` writes the *running platform's*
  ending, so it would rewrite all 1,265 lines of notebook 4 on Windows and all
  6,500 of notebook 2 on Linux, for nothing.

### The 138,000-character line, and why it has to stay

The payload is one string in one `source` entry, so the `.ipynb` contains a
single ~138,000-character line. It makes the file awkward for anything that
reads line by line — use `nbcell.py` below rather than trying to shorten it.

**Do not split the payload across `source` entries.** It looks like it works and
it does not:

- Python's `nbformat` concatenates `source` with `"".join()`, so a chunked data
  URI rejoins perfectly and every Python-side check passes.
- JupyterLab's and VS Code's `concatMultilineString` instead **appends a newline
  to every entry that does not already end in one**. A chunked payload comes
  back with a newline every chunk, and since a markdown link destination cannot
  contain a newline, the image silently fails to render — no error, just a
  broken image.

Tried on 2026-09-15 with 34 chunks of 4 KB: every Python assertion passed and
the map vanished in the VS Code notebook editor. There is no split that
satisfies both readers, so the long line is the price of a figure that renders
everywhere.

### What the generator checks for you

`make_example_4_map.py` cannot see its own output, so it verifies instead of
assuming, and raises rather than shipping something broken:

- **the voyage stays at sea.** Every waypoint and a dense sample along every leg
  is ray-cast against the country polygons. Narrow water a 1:110m basemap cannot
  resolve — the Panama Canal, the Dover Strait, the Strait of Magellan — is
  listed in `SEA_EXEMPT_BOXES`, which exempts the *check*, not the route.
- **no label collides.** Every text box is measured with real font metrics,
  padded, and required to clear every other box. The solver tries a list of
  candidate offsets per label and raises if none is free.
- **arrowheads are clear** of the port dots and of each other.

### Things worth knowing before editing

- **`SHIP_SEGMENTS`** picks which route segments carry a ship icon. The case is a
  fleet of 300, so several hulls are drawn — illustrative, not a count. Each
  icon's swept circle is reserved in the layout, so adding one pushes the text
  labels around and can make the label solver run out of room.
- **Plant positions are tied to the deck.** Each icon sits at the origin of its
  delivery leg, and the legs are labelled with the distances from
  `includes/bunker_logistics.inc`. Do not move an icon without moving its leg
  and re-checking the distance.
- **A removed label keeps its reserved box.** The IMO Net-Zero Framework and CII
  note is gone because the deck no longer carries those instruments, but its
  reservation stays, so removing the text does not let every other label reflow
  into the corner.

## Adding any other figure — `fig_to_notebook.py`

The general version of the map script. It takes a PNG and swaps it in for a
`{admonition} Figure to add` placeholder inside a cell, leaving the rest of that
cell alone:

```bash
python docs/_figures/fig_to_notebook.py docs/_figures/Regulation_example_4.png \
       docs/workshop/02-vessel-case-study.ipynb 84278b62 \
       --alt "screen-reader description" --caption "one line under the image"
```

Once a figure is in, replace it with a newer file using `--update`, which
rewrites only the image and leaves the prose, the caption and the alt text
alone. **Repeat the same `--colors` and `--max-width`**, or the image silently
changes size:

```bash
# the regulation figure in notebook 2, in its own cell under the section title
python docs/_figures/fig_to_notebook.py docs/_figures/Regulation_example_4.png \
       docs/workshop/02-vessel-case-study.ipynb ae9ec5ab \
       --update --max-width 2000 --colors 128
```

128 colours was checked by eye on that figure: the small legislation text stays
crisp and the hatched area shows no banding, at 240 KB rather than 304 KB.

`--dry-run` reports the sizes and writes nothing. Two things it does for you:

- **Shrinks the image.** A source PNG is usually far bigger than a notebook
  needs and base64 adds a third on top. It downscales to `--max-width` (2000 px
  by default, enough for a high-DPI screen) and quantises to `--colors` (256 by
  default). On the regulation figure that is 862 KB → 247 KB with no visible
  change: 4052 px wide is wasted, and a flat diagram's anti-aliased hatching
  invents thousands of near-identical shades that a palette collapses. Pass
  `--colors 0` to keep truecolour, which is only worth it for photographs.
- **Leaves the source file untouched**, so the committed PNG stays the version
  to re-edit.

It writes a single-entry, single-line payload for the reason in the section
above. Do not hand-edit an embedded image; re-run the script.

## Editing notebook 2 — `nbcell.py`

Notebook 2 is 258 KB, half of it the map. That is too big for most tools to load
whole, so edit it one cell at a time instead:

```bash
python docs/_figures/nbcell.py list docs/workshop/02-vessel-case-study.ipynb
python docs/_figures/nbcell.py find docs/workshop/02-vessel-case-study.ipynb "CASES = {"
python docs/_figures/nbcell.py get  docs/workshop/02-vessel-case-study.ipynb e77ec445 -o cell.py
# edit cell.py with anything
python docs/_figures/nbcell.py set  docs/workshop/02-vessel-case-study.ipynb e77ec445 -i cell.py

# add a new cell after (or --before) an existing one
python docs/_figures/nbcell.py insert docs/workshop/02-vessel-case-study.ipynb e77ec445 \
       -i new_cell.md --type markdown
```

A cell is addressed by id, by index, or by any unique fragment of its text; ids
come from `list` and `find`. The file is rewritten in exactly the format
nbformat produces, so **the diff is the one cell you edited** — no reformatting
of the other 86.

Three things it refuses to do, each of which has actually happened here:

- **write a generated cell.** The map cell is marked `(generated)` and rejected;
  re-run `map_to_notebook.py` instead. Editing 135 KB of base64 by hand is not
  something to do by accident, and a stray newline in it breaks the image.
- **save a code cell that does not parse.** `ast.parse` runs first, so a typo is
  reported instead of committed into a notebook nobody can open.
- **smuggle in a BOM or CRLF.** Input is read as `utf-8-sig` and cells are
  written back with `\n`, because a BOM inside cell source is invisible in a
  diff and breaks the cell at runtime.

It also re-reads the cell after writing and fails loudly if it does not come
back byte-identical.

### Dependencies

`matplotlib` for font metrics, and headless Chrome for the raster step
(`render_map_png.py` searches the usual install paths). `ne_110m_countries.geojson`
is Natural Earth 1:110m Admin 0 countries, public domain, kept here so the map is
reproducible without a download.
