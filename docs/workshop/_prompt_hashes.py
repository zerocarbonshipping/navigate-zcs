# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Say which full prompts in prompt-bank.md changed since they were last tested.

Each bank entry that holds a full prompt (a ````text block) carries a marker
`<!-- tested-prompt: <hash> -->`: the fingerprint of the prompt's text when it
last passed its test. Run from the repository root:

    python docs/workshop/_prompt_hashes.py                 # list every entry, and whether it changed
    python docs/workshop/_prompt_hashes.py --record rhine  # after a test passes: record its text as tested
    python docs/workshop/_prompt_hashes.py --ci            # in the workshop check: a warning per changed entry

The fingerprint ignores line endings and trailing spaces, nothing else: any change
of wording counts. See docs/workshop/AGENTS.md, "How much to test".
"""

import hashlib
import re
import sys
from pathlib import Path

BANK = Path("docs/workshop/prompt-bank.md")
ENTRY = re.compile(r"<!-- bank:([\w-]+) -->\n(.*?)<!-- /bank:\1 -->", re.S)
PROMPT = re.compile(r"^````text\n(.*?)^````$", re.S | re.M)
MARKER = re.compile(r"<!-- tested-prompt: (\w+) -->")


def fingerprint(text):
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    return hashlib.sha256("\n".join(lines).strip().encode("utf-8")).hexdigest()[:12]


def entries(bank):
    """(slug, current fingerprint, recorded fingerprint or None) for each entry with a full prompt."""
    for m in ENTRY.finditer(bank):
        slug, body = m.group(1), m.group(2)
        prompts = PROMPT.findall(body)
        if not prompts:
            continue
        recorded = MARKER.search(body)
        yield slug, fingerprint("\n".join(prompts)), recorded.group(1) if recorded else None


def record(bank, slug):
    for s, now, was in entries(bank):
        if s != slug:
            continue
        m = ENTRY.search(bank, bank.index(f"<!-- bank:{slug} -->"))
        body = m.group(2)
        if was is None:
            # the marker goes right after the opening one, out of the rendered text
            new = body.replace("\n", f"<!-- tested-prompt: {now} -->\n", 1) if body.startswith("\n") \
                else f"<!-- tested-prompt: {now} -->\n" + body
        else:
            new = MARKER.sub(f"<!-- tested-prompt: {now} -->", body, count=1)
        return bank[:m.start(2)] + new + bank[m.end(2):]
    sys.exit(f"no bank entry {slug!r} with a full prompt")


def main(args):
    raw = BANK.read_bytes().decode("utf-8")
    bank = raw.replace("\r\n", "\n")
    if args[:1] == ["--record"]:
        for slug in args[1:]:
            bank = record(bank, slug)
        BANK.write_bytes((bank.replace("\n", "\r\n") if "\r\n" in raw else bank).encode("utf-8"))
        args = []
    ci = args[:1] == ["--ci"]
    for slug, now, was in entries(bank):
        state = "never recorded" if was is None else ("tested" if now == was else "changed since its test")
        if ci and state != "tested":
            print(f"::warning file={BANK}::prompt bank entry '{slug}': {state}; test it before the next workshop")
        elif not ci:
            print(f"  {slug:24} {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
