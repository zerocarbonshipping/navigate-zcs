# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Put a rendered map into its workshop notebook as a base64 PNG in markdown.

Run from anywhere:

    python docs/_figures/map_to_notebook.py                     # example_4
    python docs/_figures/map_to_notebook.py reference_scenario

A map has been through three forms, and only the third survives every viewer:

  1. inline <svg> in markdown  - stripped by Colab's markdown sanitizer;
  2. image/svg+xml cell output - stripped by the notebook trust model until the
     cell is run, which is exactly what we are trying to avoid;
  3. base64 PNG in markdown    - a plain markdown image. No HTML to sanitize, no
     output to trust, no cell to run. Renders in Colab, JupyterLab, the Sphinx
     site and GitHub's notebook preview alike.

docs/_static/<stem>.svg stays the source of truth; this only changes what the
notebook carries. The target cell is found by its alt text, not by index.

The payload goes in as ONE string, which means one very long line in the
.ipynb. That is ugly and it defeats line-based tooling, but it is required.

Do not try to split it across `source` entries to shorten the line. Python's
nbformat concatenates `source` with "".join(), so chunking looks correct from
Python - but the JavaScript front-ends do not. JupyterLab's and VS Code's
`concatMultilineString` appends a newline to every entry that does not already
end in one, so a chunked data URI comes back with a newline every chunk and the
image silently fails to render. Tried on 2026-09-15; the map disappeared in the
VS Code notebook editor while every Python-side check still passed.

A markdown link destination cannot contain a newline, so there is no split that
survives both readers. One long line it is.

Line endings are PRESERVED, not imposed. The two notebooks do not agree -
notebook 2 is CRLF on disk and notebook 4 is LF - and `Path.write_text` would
write the running platform's ending to both, rewriting every line of one of
them for nothing.
"""

import argparse
import base64
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
WORKSHOP = HERE.parent / "workshop"

# Each map: the PNG stem (shared with docs/_static/<stem>.svg and written by
# render_map_png.py), the notebook that carries it, its alt text, and the
# prefix that locates the cell. The alt text IS the locator, so changing it
# here without re-running this script orphans the cell.
MAPS = {
    "example_4": {
        "stem": "example_4_map",
        "notebook": "02-vessel-case-study.ipynb",
        "alt": ("Map of the Chile to Rotterdam copper trade: the two bunker "
                "ports, a fleet of ships on the voyage via the Panama Canal, "
                "and the fuel production sites in Patagonia and southern "
                "Sweden, both of which make e-methanol and e-ammonia, with "
                "bio-methanol in Sweden as well"),
        "starts": "![Map of the Chile to Rotterdam",
    },
    "reference_scenario": {
        "stem": "reference_scenario_map",
        "notebook": "04-run-a-reference-scenario.ipynb",
        "alt": ("Map of the Navigate reference scenario: five fuel-supply "
                "regions shaded by their 2050 electricity cost, with Europe "
                "ringed as the EU ETS and FuelEU jurisdiction"),
        "starts": "![Map of the Navigate reference scenario",
    },
}


def embed(spec, dry_run=False):
    png = HERE / f"{spec['stem']}.png"
    notebook = WORKSHOP / spec["notebook"]
    if not png.exists():
        raise SystemExit(f"no rendered PNG at {png}; run render_map_png.py first")

    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    markdown = f"![{spec['alt']}](data:image/png;base64,{b64})"

    raw = notebook.read_bytes()
    crlf = raw.count(b"\r\n")
    newline = "\r\n" if crlf >= raw.count(b"\n") - crlf else "\n"
    nb = json.loads(raw.decode("utf-8"))

    # locate the figure cell by content, so a cell inserted above cannot break it
    hits = [i for i, c in enumerate(nb["cells"])
            if c["cell_type"] == "markdown"
            and "".join(c["source"]).startswith(spec["starts"])]
    if len(hits) != 1:
        raise SystemExit(f"expected exactly one map cell, found {hits}")
    idx = hits[0]

    # one entry, one line. See the module docstring before changing this.
    # replace the source in place rather than the whole cell: a cell dict also
    # carries an `id`, which nbformat 4.5 requires and which Jupyter regenerates
    # if it goes missing - churning the diff for no reason
    cell = nb["cells"][idx]
    cell["cell_type"] = "markdown"
    cell["source"] = [markdown]
    cell.setdefault("metadata", {})

    body = (json.dumps(nb, indent=1, ensure_ascii=False) + "\n").replace("\n", newline)
    print(f"notebook                 : {notebook.name}")
    print(f"line ending preserved    : {'CRLF' if newline == chr(13) + chr(10) else 'LF'}")
    if dry_run:
        print(f"map cell index           : {idx}  (dry run, nothing written)")
        return
    notebook.write_bytes(body.encode("utf-8"))

    # --- verify ---------------------------------------------------------------
    after = notebook.read_bytes()
    chk = json.loads(after.decode("utf-8"))
    src = "".join(chk["cells"][idx]["source"])
    longest = max(len(line) for line in after.decode("utf-8").split("\n"))
    entries = len(chk["cells"][idx]["source"])
    print(f"notebook cells           : {len(chk['cells'])}")
    print(f"map cell index           : {idx}")
    print(f"markdown image, no HTML  : {src.startswith('![') and '<' not in src}")
    # the front-end check that matters: one source entry, no newline anywhere.
    # A chunked payload passes a Python-side "".join() test and still fails to
    # render in JupyterLab and VS Code.
    print(f"single source entry      : {entries == 1}")
    print(f"no newline in the URI    : {chr(10) not in src}")
    print(f"png payload round-trips  : "
          f"{base64.b64decode(src.split('base64,')[1].rstrip(')')) == png.read_bytes()}")
    print(f"map cell size            : {len(src) / 1024:.0f} KB in {entries} entry")
    print(f"longest line in the file : {longest:,} chars")
    print(f"notebook file size       : {len(after) / 1024:.0f} KB")
    print(f"any <svg> anywhere       : {'<svg' in json.dumps(chk)}")
    crlf_after = after.count(b"\r\n")
    print(f"line endings after       : CRLF={crlf_after:,} "
          f"bare-LF={after.count(chr(10).encode()) - crlf_after:,}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("map", nargs="?", default="example_4", choices=sorted(MAPS),
                        help="which map to embed (default: example_4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would happen and write nothing")
    args = parser.parse_args()
    embed(MAPS[args.map], dry_run=args.dry_run)


if __name__ == "__main__":
    main()
