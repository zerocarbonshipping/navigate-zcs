# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Read and write one notebook cell at a time, as a plain text file.

Notebook 2 carries the case map as a 135 KB base64 PNG in markdown - the only
form that renders in Colab, JupyterLab, Sphinx and GitHub without running a cell
(see map_to_notebook.py). The cost is a 258 KB .ipynb that generic notebook
tooling will not open, and that no editor or assistant can load whole.

This makes that irrelevant: pull one cell out to a text file, edit it with
ordinary tools, push it back. Nothing else in the notebook is touched, and the
file is rewritten in exactly the format nbformat produces, so the diff is the
cell you edited and nothing else.

    python docs/_figures/nbcell.py list   NB
    python docs/_figures/nbcell.py get    NB CELL [-o FILE]
    python docs/_figures/nbcell.py set    NB CELL -i FILE
    python docs/_figures/nbcell.py insert NB CELL -i FILE [--type markdown] [--before]
    python docs/_figures/nbcell.py find   NB PATTERN
    python docs/_figures/nbcell.py patch  NB -i PAYLOAD.json [--dry-run]

CELL is a cell id (`9274c537`), an index (`2`), or a unique substring of the
cell's text. `list` and `find` print ids, so start there.

A cell holding generated content - the map's data URI - is marked (generated)
and refused by `set`: re-run its generator instead. Code cells are parsed before
the write, so a syntax error is reported rather than saved.

`patch` replaces a whole span of cells in ONE write, and is the command to use
for anything bigger than a couple of cells. `set` and `insert` each rewrite the
file from their own read, so restructuring a section with thirty calls means
thirty windows in which a notebook open in an editor can save over the work. It
has happened. `patch` takes a single JSON payload, checks that the span is still
exactly the cells the payload was written against, and refuses rather than
guessing if anything moved - see cmd_patch for the payload shape.
"""

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import uuid

FORMAT = dict(indent=1, ensure_ascii=False)   # what nbformat writes


def load(path):
    nb = json.loads(path.read_text(encoding="utf-8"))
    return nb, [(i, c, "".join(c["source"])) for i, c in enumerate(nb["cells"])]


def save(path, nb):
    path.write_text(json.dumps(nb, **FORMAT) + "\n", encoding="utf-8")


def save_atomic(path, nb):
    """Write via a same-directory temp file and os.replace.

    A half-written notebook is unopenable, and this file is routinely open in an
    editor while scripts touch it. os.replace is atomic on Windows and POSIX
    alike. The retry is for the editor's or OneDrive's file watcher briefly
    holding a handle, which does happen on this path.
    """
    payload = json.dumps(nb, **FORMAT) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
        for attempt in range(3):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.4)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


MAGIC_LINE = re.compile(r"^(\s*)[%!]")


def check_syntax(src):
    """ast.parse notebook code, tolerating IPython magics.

    Notebook cells legitimately use `%time`, `!unzip` and friends, which are not
    Python - IPython rewrites them before execution. A plain ast.parse rejects
    the whole cell over one such line, which would mean this tool refuses to
    write any cell containing a magic (notebook 2 has two). Blank the magic
    lines out, keeping their indentation so block structure survives, and check
    everything else. A cell magic (`%%…`) on the first line makes the entire
    cell non-Python, so there is nothing to check.

    Raises SyntaxError, like ast.parse, so callers report it the same way.
    """
    if src.lstrip().startswith("%%"):
        return
    ast.parse("\n".join(
        (match.group(1) + "pass") if (match := MAGIC_LINE.match(line)) else line
        for line in src.split("\n")
    ))


def is_generated(text):
    return "data:image" in text or "base64," in text


def resolve(cells, key):
    """Find one cell by id, index, or a unique substring of its source."""
    for i, cell, text in cells:
        if cell.get("id") == key:
            return i, cell, text

    if key.isdigit() and int(key) < len(cells):
        return cells[int(key)]

    hits = [c for c in cells if key in c[2]]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"no cell matches {key!r} - try `list` or `find`")
    sys.exit(f"{key!r} matches {len(hits)} cells "
             f"(indices {[h[0] for h in hits]}) - use an id or an index")


def cmd_list(args):
    _, cells = load(args.notebook)
    print(f"{'idx':>4}  {'id':<10} {'type':<9} {'lines':>5} {'chars':>8}  first line")
    for i, cell, text in cells:
        first = next((line for line in text.splitlines() if line.strip()), "")
        mark = " (generated)" if is_generated(text) else ""
        print(f"{i:>4}  {cell.get('id', '-'):<10} {cell['cell_type']:<9} "
              f"{len(text.splitlines()):>5} {len(text):>8}  {first[:64]}{mark}")


def cmd_find(args):
    _, cells = load(args.notebook)
    for i, cell, text in cells:
        for n, line in enumerate(text.splitlines(), 1):
            if args.pattern in line:
                print(f"{i:>4} {cell.get('id', '-'):<10} line {n:<4} {line.strip()[:100]}")


def cmd_get(args):
    _, cells = load(args.notebook)
    i, cell, text = resolve(cells, args.cell)

    if args.output:
        # newline="\n": the notebook stores "\n", so write the same and the
        # round trip cannot smuggle CRLF into a cell on Windows
        with args.output.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"cell {i} (id={cell.get('id', '-')}, {cell['cell_type']}, "
              f"{len(text)} chars) -> {args.output}")
        if is_generated(text):
            print("note: this cell is generated - edit its generator, not this file")
    else:
        sys.stdout.write(text)


def cmd_set(args):
    nb, cells = load(args.notebook)
    i, cell, old = resolve(cells, args.cell)
    # utf-8-sig: editors on Windows routinely add a BOM, and a BOM inside cell
    # source is invisible in a diff but breaks the cell when it runs
    new = args.input.read_text(encoding="utf-8-sig")

    if is_generated(old) and not args.force:
        sys.exit(f"cell {i} holds generated content (a data URI). Re-run its "
                 f"generator - for the case map, docs/_figures/map_to_notebook.py. "
                 f"Pass --force only if you really mean to hand-edit it.")

    if cell["cell_type"] == "code" and not args.no_syntax_check:
        try:
            check_syntax(new)
        except SyntaxError as exc:
            sys.exit(f"refusing to write: {args.notebook.name} cell {i} would not "
                     f"parse - {exc.msg} at line {exc.lineno}")

    if new == old:
        print(f"cell {i} unchanged - nothing written")
        return

    # nbformat convention: one list element per line, newlines kept
    nb["cells"][i]["source"] = new.splitlines(keepends=True)
    save(args.notebook, nb)

    check = "".join(json.loads(args.notebook.read_text(encoding="utf-8"))["cells"][i]["source"])
    if check != new:
        sys.exit("WROTE A CELL THAT DOES NOT READ BACK IDENTICALLY - check git diff")
    print(f"cell {i} (id={cell.get('id', '-')}) updated: "
          f"{len(old)} -> {len(new)} chars, reads back identical")


def cmd_insert(args):
    nb, cells = load(args.notebook)
    i, cell, _ = resolve(cells, args.cell)
    new = args.input.read_text(encoding="utf-8-sig")

    if args.type == "code" and not args.no_syntax_check:
        try:
            check_syntax(new)
        except SyntaxError as exc:
            sys.exit(f"refusing to insert: would not parse - {exc.msg} at line {exc.lineno}")

    at = i if args.before else i + 1
    fresh = {
        "cell_type": args.type,
        # nbformat 4.5 requires an id; Jupyter mints one otherwise and churns the diff
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": new.splitlines(keepends=True),
    }
    if args.type == "code":
        fresh["execution_count"] = None
        fresh["outputs"] = []

    nb["cells"].insert(at, fresh)
    save(args.notebook, nb)

    check = json.loads(args.notebook.read_text(encoding="utf-8"))
    if "".join(check["cells"][at]["source"]) != new:
        sys.exit("INSERTED A CELL THAT DOES NOT READ BACK IDENTICALLY - check git diff")
    print(f"inserted {args.type} cell at index {at} (id={fresh['id']}, {len(new)} chars), "
          f"{'before' if args.before else 'after'} cell {i} (id={cell.get('id', '-')}); "
          f"notebook now has {len(check['cells'])} cells")


def cmd_patch(args):
    """Replace a span of cells, and optionally edit named cells outside it, in one write."""
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    nb, cells = load(args.notebook)
    by_id = {c.get("id"): (i, c, t) for i, c, t in cells}

    # ---- preconditions. Any failure aborts with nothing written ----------
    problems = []

    span = payload["span"]
    if span["first_id"] not in by_id:
        problems.append(f"span first_id {span['first_id']!r} is not in the notebook")
    if span["last_id"] not in by_id:
        problems.append(f"span last_id {span['last_id']!r} is not in the notebook")

    if not problems:
        first = by_id[span["first_id"]][0]
        last = by_id[span["last_id"]][0]
        if first > last:
            problems.append(f"span is inverted: {span['first_id']} at {first} "
                            f"comes after {span['last_id']} at {last}")

        # The headings are an independent check on the ids. An id proves identity,
        # not content: a cell keeps its id through any amount of rewriting. If the
        # two disagree, the notebook is not the shape the payload assumes.
        for key, heading in (("first_id", span.get("first_heading")),
                             ("last_id", span.get("last_heading"))):
            if not heading:
                continue
            want = by_id[span[key]][0]
            hits = [i for i, _c, t in cells if heading in t]
            if hits != [want]:
                problems.append(f"{heading!r} is in cells {hits}, but {span[key]} "
                                f"is cell {want} - the span has moved")

    if not problems:
        found = [c.get("id") for _i, c, _t in cells[first:last + 1]]
        if found != payload["expect_ids"]:
            problems.append(
                "the span is not the cells this payload was written against.\n"
                f"    expected {len(payload['expect_ids'])} cells: {payload['expect_ids']}\n"
                f"    found    {len(found)} cells: {found}\n"
                "    Someone edited inside the span. Re-derive the payload; do not merge.")

    for edit in payload.get("edits_outside_span", []):
        if edit["id"] not in by_id:
            problems.append(f"out-of-span edit target {edit['id']!r} is gone")
            continue
        i, _c, text = by_id[edit["id"]]
        if not problems and first <= i <= last:
            problems.append(f"out-of-span edit {edit['id']!r} is inside the span (cell {i})")
        if "expect_sha256" in edit and digest(text) != edit["expect_sha256"]:
            problems.append(f"cell {edit['id']} (index {i}) has changed since the payload "
                            f"was written: {digest(text)} != {edit['expect_sha256']}")

    for n, cell in enumerate(payload["cells"]):
        if is_generated("".join(cell["source"]) if isinstance(cell["source"], list)
                        else cell["source"]):
            problems.append(f"new cell {n} carries generated content - use its generator")
        if cell["cell_type"] == "code":
            body = ("".join(cell["source"]) if isinstance(cell["source"], list)
                    else cell["source"])
            try:
                check_syntax(body)
            except SyntaxError as exc:
                problems.append(f"new cell {n} would not parse - {exc.msg} at line {exc.lineno}")

    if problems:
        sys.exit("refusing to patch:\n  - " + "\n  - ".join(problems))

    # ---- build the new cell list -----------------------------------------
    def normalise(cell):
        body = ("".join(cell["source"]) if isinstance(cell["source"], list)
                else cell["source"])
        out = {
            "cell_type": cell["cell_type"],
            "id": cell.get("id") or uuid.uuid4().hex[:8],
            "metadata": cell.get("metadata", {}),
            "source": body.splitlines(keepends=True),
        }
        if cell["cell_type"] == "code":
            out["execution_count"] = None
            out["outputs"] = []
        return out

    replacement = [normalise(c) for c in payload["cells"]]
    kept_before, kept_after = nb["cells"][:first], nb["cells"][last + 1:]
    nb["cells"] = kept_before + replacement + kept_after

    # out-of-span edits are applied by id on the rebuilt list, so an index shift
    # from a span of a different length cannot put them on the wrong cell
    moved = {c.get("id"): n for n, c in enumerate(nb["cells"])}
    for edit in payload.get("edits_outside_span", []):
        n = moved[edit["id"]]
        nb["cells"][n]["source"] = edit["source"].splitlines(keepends=True)

    if args.dry_run:
        print(f"preconditions pass. would replace cells {first}-{last} "
              f"({last - first + 1} -> {len(replacement)}) and edit "
              f"{len(payload.get('edits_outside_span', []))} cells outside the span; "
              f"notebook {len(cells)} -> {len(nb['cells'])} cells. Nothing written.")
        return

    # re-stat immediately before writing: if the file moved under us between the
    # read at the top and here, the whole precondition set is stale
    stat_now = args.notebook.stat()
    if (payload.get("stat_mtime_ns") is not None
            and stat_now.st_mtime_ns != payload["stat_mtime_ns"]):
        sys.exit(f"refusing to patch: {args.notebook.name} changed on disk since the "
                 f"payload was built (mtime {stat_now.st_mtime_ns} != "
                 f"{payload['stat_mtime_ns']}). Re-derive the payload.")

    save_atomic(args.notebook, nb)

    # ---- read back and prove every written cell round-tripped ------------
    check, check_cells = load(args.notebook)
    back = {c.get("id"): t for _i, c, t in check_cells}
    for cell in replacement:
        want = "".join(cell["source"])
        if back.get(cell["id"]) != want:
            sys.exit(f"WROTE CELL {cell['id']} THAT DOES NOT READ BACK IDENTICALLY "
                     f"- check git diff")
    for edit in payload.get("edits_outside_span", []):
        if back.get(edit["id"]) != edit["source"]:
            sys.exit(f"WROTE CELL {edit['id']} THAT DOES NOT READ BACK IDENTICALLY "
                     f"- check git diff")

    print(f"patched cells {first}-{last} ({last - first + 1} -> {len(replacement)}), "
          f"edited {len(payload.get('edits_outside_span', []))} outside the span; "
          f"notebook now {len(check['cells'])} cells, all written cells read back identical")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, *, cell=False, pattern=False):
        p = sub.add_parser(name, help=func.__doc__)
        p.add_argument("notebook", type=pathlib.Path)
        if cell:
            p.add_argument("cell", help="cell id, index, or unique text fragment")
        if pattern:
            p.add_argument("pattern")
        p.set_defaults(func=func)
        return p

    add("list", cmd_list)
    add("find", cmd_find, pattern=True)

    p_get = add("get", cmd_get, cell=True)
    p_get.add_argument("-o", "--output", type=pathlib.Path,
                       help="write the cell here instead of stdout")

    p_set = add("set", cmd_set, cell=True)
    p_set.add_argument("-i", "--input", type=pathlib.Path, required=True)
    p_set.add_argument("--force", action="store_true",
                       help="allow writing a generated cell")
    p_set.add_argument("--no-syntax-check", action="store_true",
                       help="skip ast.parse on code cells")

    p_ins = add("insert", cmd_insert, cell=True)
    p_ins.add_argument("-i", "--input", type=pathlib.Path, required=True)
    p_ins.add_argument("--type", choices=("markdown", "code"), default="markdown")
    p_ins.add_argument("--before", action="store_true",
                       help="insert before the named cell instead of after it")
    p_ins.add_argument("--no-syntax-check", action="store_true",
                       help="skip ast.parse on code cells")

    p_patch = add("patch", cmd_patch)
    p_patch.add_argument("-i", "--input", type=pathlib.Path, required=True,
                         help="JSON payload: span, expect_ids, cells, edits_outside_span")
    p_patch.add_argument("--dry-run", action="store_true",
                         help="check the preconditions and report, writing nothing")

    args = parser.parse_args()
    if not args.notebook.is_file():
        sys.exit(f"no such notebook: {args.notebook}")
    args.func(args)


if __name__ == "__main__":
    main()
