# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Check that each tutorial notebook holds one clean run of it.

The documentation shows a notebook with the outputs saved in it and never runs
it, so those outputs must come from one run from a fresh kernel, without
errors, with every plot, and with the setup cell's ROOT left at Colab's
/content. Without arguments it checks every notebook under docs/tutorials/; a
pre-commit hook can pass the notebooks it commits instead.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NOTEBOOKS = Path(__file__).parent / "tutorials"

# a shell command such as !navigate prints its error as plain text, and Horizon
# logs it at the ERROR level
ERROR_TEXT = re.compile(r"^(Traceback|Error:)|- ERROR -", re.MULTILINE)

HOW_TO_REFRESH = """
To refresh a notebook's outputs:
  1. Set ROOT in its setup cell to a folder of your own.
  2. Restart the kernel and run all cells.
  3. Set ROOT back to "/content"; the outputs stay.
  4. Save the notebook and run this check again: python docs/check_notebooks.py
  5. Commit the notebook."""


def find_problems(path: Path) -> list[str]:
    """Return what keeps a notebook from being one clean run, if anything."""
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    code = [cell for cell in cells if cell["cell_type"] == "code"]
    problems = []

    # 'restart the kernel and run all cells' numbers the cells 1, 2, ... in
    # order; a cell run twice, skipped or run out of order breaks the sequence.
    # VS Code clears a cell's number when it is edited after the run, as the
    # setup cell is when ROOT is set back to /content, so that one may be missing
    expected = list(range(1, len(code) + 1))
    counts = [
        number
        if cell["execution_count"] is None and is_setup(cell)
        else cell["execution_count"]
        for number, cell in zip(expected, code, strict=True)
    ]
    if counts != expected:
        problems.append(
            "not one run from a fresh kernel: restart the kernel and run all cells"
        )

    for cell in code:
        name = f"cell {cell.get('id', '?')}"
        source = "".join(cell["source"])
        outputs = cell["outputs"]
        text = "".join("".join(output.get("text", "")) for output in outputs)

        has_error = any(output["output_type"] == "error" for output in outputs)
        has_plot = any("text/html" in output.get("data", {}) for output in outputs)

        if not outputs:
            problems.append(f"{name} has no output")
        if has_error or ERROR_TEXT.search(text):
            problems.append(f"{name} shows an error")
        if "show(" in source and not has_plot:
            problems.append(f"{name} shows no plot")
        if is_setup(cell) and not source.startswith('ROOT = "/content"'):
            problems.append(f"{name}: ROOT is not /content")

    return [f"{path}: {problem}" for problem in problems]


def is_setup(cell: dict) -> bool:
    """Tell whether a code cell is the setup cell, which sets ROOT."""
    return "".join(cell["source"]).startswith("ROOT = ")


if __name__ == "__main__":
    paths = [Path(arg) for arg in sys.argv[1:]] or sorted(
        NOTEBOOKS.glob("notebook_*/*.ipynb")
    )
    problems = [problem for path in paths for problem in find_problems(path)]
    if problems:
        sys.exit("\n".join(problems) + "\n" + HOW_TO_REFRESH)

    print("Success!")
