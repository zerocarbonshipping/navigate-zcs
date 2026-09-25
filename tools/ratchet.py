#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# tools/ratchet.py — generate or prune the legacy-file ratchet lists.
#
# The ratchet enumerates pre-existing violations so the full rule set can gate
# CI from day one: ruff entries live in a generated region of the repo's
# .ruff.toml ([lint.extend-per-file-ignores]), mypy entries in a generated
# region of mypy.ini ([mypy-<module>] ignore_errors sections). New files are
# never on a list, so new code is always fully checked. Entries only ever
# shrink: default runs write the current violation set (bootstrap), --prune
# intersects the existing entries with current violations and can only remove.
#
# Regenerating is a maintainer operation, not the ordinary way to answer an
# entry: a contributor cleans the file and deletes its entry. Regeneration
# temporarily blanks the generated region in the working tree (so existing
# entries do not mask the violations they suppress), runs the underlying
# tool, and always restores/rewrites the file afterwards.
#
# Usage:
#   ratchet.py ruff [--repo PATH] [--paths P ...] [--prune]
#   ratchet.py mypy [--repo PATH] [--paths P ...] [--prune]

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

# These marker lines are committed inside .ruff.toml / mypy.ini and must
# match those files verbatim, or the tool stops finding its regions.
MARK_BEGIN = "# >>> generated ratchet - entries may only be removed, never added >>>"
MARK_END = "# <<< generated ratchet <<<"


def split_region(text: str, path: Path) -> tuple[str, str, str]:
    """Split file text into (head, region, tail) around the marker lines."""
    lines = text.splitlines(keepends=True)
    begin = [i for i, l in enumerate(lines) if l.rstrip("\n") == MARK_BEGIN]
    end = [i for i, l in enumerate(lines) if l.rstrip("\n") == MARK_END]
    if len(begin) != 1 or len(end) != 1 or end[0] < begin[0]:
        sys.exit(f"error: {path} needs exactly one generated-ratchet marker pair")
    head = "".join(lines[: begin[0] + 1])
    region = "".join(lines[begin[0] + 1 : end[0]])
    tail = "".join(lines[end[0] :])
    return head, region, tail


def run_with_blank_region(
    config: Path, build_cmd: Callable[[Path], list[str]], cwd: Path
) -> str:
    """Run a checker against config with its generated region blanked.

    The blanked text is written to a temporary file next to config (never to
    the tracked file itself, so a concurrent reader or a killed process never
    sees an incomplete .ruff.toml / mypy.ini) and build_cmd receives that
    file's path to build the command line pointing the checker at it.
    """
    head, _, tail = split_region(config.read_text(), config)
    name_stem = Path(config.name.lstrip(".")).stem
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".ratchet-{name_stem}-", suffix=config.suffix, dir=cwd
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(head + tail)
        cmd = build_cmd(tmp)
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    finally:
        tmp.unlink(missing_ok=True)
    # ruff/mypy exit 1 on findings; anything above signals a real failure.
    if proc.returncode > 1:
        sys.exit(f"error: {' '.join(cmd)} failed:\n{proc.stderr}")
    return proc.stdout


def write_region(config: Path, region: str) -> None:
    head, _, tail = split_region(config.read_text(), config)
    config.write_text(head + region + tail)


def path_is_selected(rel: str, paths: list[str]) -> bool:
    """Whether rel (a repo-relative file) falls under one of paths.

    A prune run only observes violations under --paths, so only entries this
    check accepts may be intersected with what the run found; every other
    entry falls outside what the run could see and must carry over as is.
    """
    rel_path = PurePosixPath(rel)
    return any(rel_path == PurePosixPath(p) or PurePosixPath(p) in rel_path.parents for p in paths)


def parse_ruff_region(region: str) -> dict[str, list[str]]:
    """Existing entries: '"file" = ["CODE", ...]' lines under the table header."""
    entries: dict[str, list[str]] = {}
    for line in region.splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("["):
            continue
        name, _, codes = line.partition("=")
        entries[name.strip().strip('"')] = [
            c.strip().strip('"') for c in codes.strip().strip("[]").split(",") if c.strip()
        ]
    return entries


def ratchet_ruff(repo: Path, paths: list[str], prune: bool) -> None:
    config = repo / ".ruff.toml"
    out = run_with_blank_region(
        config,
        lambda tmp: [
            "ruff",
            "check",
            *paths,
            "--config",
            str(tmp),
            "--output-format",
            "json",
            "--exit-zero",
        ],
        repo,
    )
    current: dict[str, set[str]] = {}
    for v in json.loads(out):
        rel = Path(v["filename"]).relative_to(repo).as_posix()
        current.setdefault(rel, set()).add(v["code"])

    if prune:
        old = parse_ruff_region(split_region(config.read_text(), config)[1])
        new = {}
        for f, codes in old.items():
            if not path_is_selected(f, paths):
                new[f] = list(codes)
                continue
            kept = sorted(set(codes) & current.get(f, set()))
            if kept:
                new[f] = kept
    else:
        new = {f: sorted(codes) for f, codes in current.items()}

    lines = ["[lint.extend-per-file-ignores]\n"] if new else []
    for f in sorted(new):
        codes = ", ".join('"' + c + '"' for c in new[f])
        lines.append(f'"{f}" = [{codes}]\n')
    write_region(config, "".join(lines))
    print(f"ruff ratchet: {len(new)} files ({config})")


def parse_mypy_region(region: str) -> list[str]:
    """Existing entries: the module names of the [mypy-<module>] sections."""
    return [
        line.strip()[len("[mypy-") : -1]
        for line in region.splitlines()
        if line.strip().startswith("[mypy-") and line.strip().endswith("]")
    ]


def module_of(rel_file: str) -> str:
    parts = Path(rel_file).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def module_is_selected(module: str, paths: list[str]) -> bool:
    """Whether module falls under one of the module prefixes paths denote.

    Mirrors path_is_selected, but --paths for mypy are module paths
    (files or packages), so the entries they cover are module names and
    dotted-prefix matches rather than filesystem ones.
    """
    return any(
        module == prefix or module.startswith(prefix + ".")
        for prefix in (module_of(p) for p in paths)
    )


def ratchet_mypy(repo: Path, paths: list[str], prune: bool) -> None:
    config = repo / "mypy.ini"
    out = run_with_blank_region(
        config,
        lambda tmp: ["mypy", *paths, "--output=json", "--config-file", str(tmp)],
        repo,
    )
    current: set[str] = set()
    for line in out.splitlines():
        d = json.loads(line)
        if d.get("severity") == "error":
            current.add(module_of(d["file"]))

    if prune:
        old = parse_mypy_region(split_region(config.read_text(), config)[1])
        new = sorted(
            m for m in old if not module_is_selected(m, paths) or m in current
        )
    else:
        new = sorted(current)

    region = "".join(f"[mypy-{m}]\nignore_errors = True\n\n" for m in new)
    write_region(config, region)
    print(f"mypy ratchet: {len(new)} modules ({config})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", choices=["ruff", "mypy"])
    parser.add_argument(
        "--repo", type=Path, default=None, help="repo root (default: this script's repository)"
    )
    parser.add_argument("--paths", nargs="+", default=None, help="paths to check, relative to the repo")
    parser.add_argument("--prune", action="store_true", help="only remove entries with no current violations")
    args = parser.parse_args()

    repo = (args.repo or Path(__file__).resolve().parent.parent).resolve()
    if not repo.is_dir():
        sys.exit(f"error: repo not found: {repo}")
    if shutil.which(args.tool) is None:
        sys.exit(f"error: {args.tool} not on PATH (run inside the repo's dev environment)")

    if args.tool == "ruff":
        ratchet_ruff(repo, args.paths or ["navigate", "tests"], args.prune)
    else:
        ratchet_mypy(repo, args.paths or ["navigate"], args.prune)


if __name__ == "__main__":
    main()
