# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Embed a PNG into a notebook cell, in place of a figure placeholder.

    python docs/_figures/fig_to_notebook.py PNG NB CELL --alt "..." [--caption "..."]
    python docs/_figures/fig_to_notebook.py ... --dry-run     # report sizes only

The general version of map_to_notebook.py, which stays as the map's own
wrapper because it carries the map's verification. Everything here follows the
same two hard-won rules:

  1. A base64 PNG in a markdown cell is the only form that renders in Colab,
     JupyterLab, the Sphinx site and GitHub without running a cell. Inline
     <svg> is stripped by Colab's sanitizer; an image cell *output* is stripped
     by the notebook trust model until the cell runs.
  2. The payload MUST be a single `source` entry on a single line. Python's
     nbformat rejoins chunks with "".join() so splitting looks fine from
     Python, but JupyterLab and VS Code append a newline to every entry that
     does not end in one - and a markdown link destination cannot contain a
     newline, so the image silently fails to render.

Source images tend to be far larger than a notebook needs, and base64 costs a
further third, so the image is downscaled and re-encoded in memory before
embedding. The file on disk is left alone as the source of truth.
"""

import argparse
import base64
import io
import json
import pathlib
import re
import sys

DEFAULT_MAX_WIDTH = 2000    # plenty for a high-DPI screen at notebook width


def optimise(path: pathlib.Path, max_width: int, colors: int | None) -> bytes:
    """Downscale to max_width and re-encode, flattening any alpha onto white.

    A flat diagram costs far more as truecolour PNG than it needs to, because
    anti-aliased edges and hatching invent thousands of near-identical shades.
    Quantising to a palette collapses those and typically saves 80 % with no
    visible change; `colors=None` keeps truecolour for photographic sources.
    """
    from PIL import Image

    with Image.open(path) as im:
        original = im.size

        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            flat = Image.new("RGB", im.size, (255, 255, 255))
            flat.paste(im, mask=im.split()[-1])
            im = flat
        else:
            im = im.convert("RGB")

        if im.width > max_width:
            height = round(im.height * max_width / im.width)
            im = im.resize((max_width, height), Image.LANCZOS)

        if colors:
            im = im.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)

        buf = io.BytesIO()
        im.save(buf, format="PNG", optimize=True)

    print(f"  source    : {original[0]} x {original[1]}, {path.stat().st_size / 1024:.0f} KB")
    print(f"  embedded  : {im.width} x {im.height}, {len(buf.getvalue()) / 1024:.0f} KB "
          f"({len(buf.getvalue()) * 4 / 3 / 1024:.0f} KB as base64)")
    return buf.getvalue()


IMAGE_LINE = re.compile(r"^!\[([^\]]*)\]\(data:image/[a-z]+;base64,[A-Za-z0-9+/=]*\)$")


def replace_placeholder(source: str, markdown: str, title: str) -> str:
    """Swap a ```{admonition} <title> ... ``` block for the image markdown."""
    pattern = re.compile(
        r"^```\{admonition\}[ \t]*" + re.escape(title) + r"[ \t]*\n.*?^```[ \t]*\n",
        re.DOTALL | re.MULTILINE)

    hits = pattern.findall(source)
    if len(hits) != 1:
        sys.exit(f"expected exactly one '{title}' admonition in the cell, found {len(hits)}. "
                 f"If the figure is already embedded and you are replacing it with a newer "
                 f"file, pass --update.")

    return pattern.sub(lambda _: markdown, source, count=1)


def replace_image(source: str, payload: str, alt: str | None) -> str:
    """Swap the payload of an already-embedded image, keeping the surrounding text.

    Updating a figure should not disturb the prose or the caption around it, so
    only the one image line is rewritten. The existing alt text is kept unless a
    new one is given.
    """
    lines = source.split("\n")
    hits = [i for i, line in enumerate(lines) if IMAGE_LINE.match(line)]

    if len(hits) != 1:
        sys.exit(f"expected exactly one embedded image in the cell, found {len(hits)}")

    i = hits[0]
    old_alt = IMAGE_LINE.match(lines[i]).group(1)
    lines[i] = f"![{alt or old_alt}](data:image/png;base64,{payload})"
    print(f"  alt text  : {'replaced' if alt else 'kept'} ({len(alt or old_alt)} chars)")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("png", type=pathlib.Path)
    p.add_argument("notebook", type=pathlib.Path)
    p.add_argument("cell", help="cell id, index, or unique text fragment")
    p.add_argument("--alt", help="alt text; it is what a screen reader reads. "
                                 "Required unless --update, which keeps the existing alt")
    p.add_argument("--caption", help="optional italic caption under the image")
    p.add_argument("--placeholder", default="Figure to add",
                   help="title of the admonition to replace (default: 'Figure to add')")
    p.add_argument("--update", action="store_true",
                   help="replace an already-embedded image with a newer file, keeping the "
                        "prose, the caption and (unless --alt) the alt text")
    p.add_argument("--whole-cell", action="store_true",
                   help="replace the entire cell instead of a placeholder inside it")
    p.add_argument("--max-width", type=int, default=DEFAULT_MAX_WIDTH)
    p.add_argument("--colors", type=int, default=256,
                   help="palette size for quantisation (default 256); 0 keeps truecolour, "
                        "which is only worth it for photographs")
    p.add_argument("--dry-run", action="store_true", help="report sizes, write nothing")
    args = p.parse_args()

    if not args.alt and not args.update:
        p.error("--alt is required unless --update is given")
    if args.update and args.whole_cell:
        p.error("--update and --whole-cell are mutually exclusive")
    if args.update and args.caption:
        p.error("--update keeps the caption that is already there; edit it with nbcell.py")

    for f in (args.png, args.notebook):
        if not f.is_file():
            sys.exit(f"no such file: {f}")

    print(f"embedding {args.png.name}")
    data = optimise(args.png, args.max_width, args.colors or None)
    b64 = base64.b64encode(data).decode("ascii")

    # one line, no newline anywhere in it - see rule 2 in the module docstring
    markdown = f"![{args.alt}](data:image/png;base64,{b64})"
    if args.caption:
        markdown += f"\n\n*{args.caption}*\n"

    nb = json.loads(args.notebook.read_text(encoding="utf-8"))
    cells = nb["cells"]

    # resolve the cell the same way nbcell.py does
    idx = None
    for i, c in enumerate(cells):
        if c.get("id") == args.cell:
            idx = i
            break
    if idx is None and args.cell.isdigit() and int(args.cell) < len(cells):
        idx = int(args.cell)
    if idx is None:
        hits = [i for i, c in enumerate(cells) if args.cell in "".join(c["source"])]
        if len(hits) != 1:
            sys.exit(f"{args.cell!r} matched {len(hits)} cells - use an id or index")
        idx = hits[0]

    old = "".join(cells[idx]["source"])
    if args.whole_cell:
        new = markdown
    elif args.update:
        new = replace_image(old, b64, args.alt)
    else:
        new = replace_placeholder(old, markdown, args.placeholder)

    print(f"  cell      : {idx} (id={cells[idx].get('id', '-')}), "
          f"{len(old)} -> {len(new)} chars")

    if args.dry_run:
        print("  dry run - nothing written")
        return

    cells[idx]["cell_type"] = "markdown"
    cells[idx]["source"] = [new]        # single entry; rule 2
    cells[idx].setdefault("metadata", {})
    args.notebook.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")

    # --- verify -----------------------------------------------------------
    chk = json.loads(args.notebook.read_text(encoding="utf-8"))
    src = "".join(chk["cells"][idx]["source"])

    # check the image line itself, not the whole cell: a caption may contain a
    # bracket, so splitting the cell on ")" is not the same thing
    image_lines = [ln for ln in src.split("\n") if ln.startswith("![")]
    grammar = re.fullmatch(r"!\[[^\]]+\]\(data:image/png;base64,([A-Za-z0-9+/=]+)\)",
                           image_lines[0]) if len(image_lines) == 1 else None

    print(f"  single source entry     : {len(chk['cells'][idx]['source']) == 1}")
    print(f"  one image, whole markdown-image on one line : {grammar is not None}")
    print(f"  payload round-trips     : "
          f"{base64.b64decode(grammar.group(1)) == data if grammar else False}")
    print(f"  valid PNG               : {data[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10])}")
    print(f"  placeholder gone        : {'admonition' not in src}")
    print(f"  notebook file size      : {args.notebook.stat().st_size / 1024:.0f} KB")

    if grammar is None:
        sys.exit("the image markdown is not intact on a single line - check git diff")


if __name__ == "__main__":
    main()
