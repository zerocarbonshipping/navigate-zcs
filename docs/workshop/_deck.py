# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Show a deck as tabs, coloured as in VS Code: Session 3's show_deck, shared.

The Examples pages that are notebooks (docs/examples/_pages/) use it; Session 3
still defines its own copy in its Setup cell. Keep the two in step.
"""

from pathlib import Path


def show_deck(root, tabs):
    """Show a deck as tabs, as on the Examples pages: `tabs` maps each tab's
    label to the files it holds, relative to `root` (a string) or to the
    repository root (a Path, for a library file the deck loads). A string
    starting "Also" is shown as a line naming more files, not their contents."""
    import html
    import json
    import sys
    import uuid
    import zipfile

    from IPython.display import display
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexer import RegexLexer
    from pygments.token import Comment, Keyword, Number, Operator, String, Text

    if str(Path("docs/workshop").resolve()) not in sys.path:
        sys.path.insert(0, str(Path("docs/workshop").resolve()))
    from _style import swatch

    def code_lines(text):
        """A file's lines without comments or blank lines, to compare a copy with its original."""
        return [ln.split("#")[0].strip() for ln in text.splitlines() if ln.split("#")[0].strip()]

    # Colour the files as the Navigate extension for VS Code does: its TextMate
    # grammar, read from the .vsix in syntax/vscode/, gives the rules in order.
    vsix = sorted(Path("syntax/vscode").glob("navigate-language-*.vsix"))[-1]
    grammar = json.loads(zipfile.ZipFile(vsix).read("extension/syntaxes/navigate.tmLanguage.json"))
    scopes = {"comment": Comment, "keyword.control": Keyword, "storage.type": Keyword.Type,
              "constant.numeric": Number, "keyword.operator": Operator}
    rules = []
    for ref in grammar["patterns"]:
        for rule in grammar["repository"][ref["include"].lstrip("#")]["patterns"]:
            if "match" in rule:
                token = next(t for s, t in scopes.items() if rule["name"].startswith(s))
                rules.append((rule["match"], token))
            else:   # the one begin/end rule: a double-quoted string
                rules.append((r'"(?:\\.|[^"\\])*"', String))
    lexer = type("NavigateLexer", (RegexLexer,), {"tokens": {"root": rules + [(r"\w+|\s+|.", Text)]}})()

    uid = f"deck-{uuid.uuid4().hex[:8]}"
    css = (f".{uid} > input {{display: none}}"
           f".{uid} > label {{display: inline-block; padding: .35em .9em; cursor: pointer;"
           f" opacity: .6; border-bottom: 2px solid transparent; font-family: sans-serif}}"
           f".{uid} > input:checked + label {{opacity: 1; border-bottom-color: currentColor}}"
           f".{uid} > div {{display: none; border-top: 1px solid rgba(128, 128, 128, .4)}}"
           f".{uid} .cap {{margin: .8em 0 .2em; font-family: sans-serif; font-size: .85em; opacity: .7}}"
           f".{uid} pre {{margin: 0; padding: .6em; overflow-x: auto; font-size: .85em;"
           f" background: rgba(128, 128, 128, .08)}}"
           # Comments keep the text colour, so they read in Colab's light and dark themes.
           f".{uid} pre .c {{font-style: italic; opacity: .75}}"
           f".{uid} pre .k {{color: {swatch('red', 4)}; font-weight: bold}}"
           f".{uid} pre .kt {{color: {swatch('blue', 6)}}}"
           f".{uid} pre .s {{color: {swatch('orange', 5)}}}"
           f".{uid} pre .m {{color: {swatch('green', 5)}}}")
    bar, panels, plain = [], [], []
    for i, (label, files) in enumerate(tabs.items()):
        checked = " checked" if i == 0 else ""
        bar.append(f'<input type="radio" name="{uid}" id="{uid}-{i}"{checked}>'
                   f'<label for="{uid}-{i}">{html.escape(label)}</label>')
        css += f"#{uid}-{i}:checked ~ .p{i} {{display: block}}"
        body = []
        for name in files:
            if isinstance(name, str) and name.startswith("Also"):
                # files laid out like one shown above: named, not shown
                body.append(f'<div class="cap">{html.escape(name)}</div>')
                plain.append(f"# {name}")
                continue
            path = name if isinstance(name, Path) else Path(root) / name
            name = Path(name).as_posix()
            text = path.read_text(encoding="utf-8")
            caption = html.escape(name)
            # A library file the workshop explains is shown from its annotated copy: the
            # same lines, plus comments. The library itself is never edited.
            copy = Path("docs/workshop/annotated") / path
            if copy.is_file():
                annotated = copy.read_text(encoding="utf-8")
                assert code_lines(annotated) == code_lines(text), f"{copy} is out of date"
                text = annotated
                caption += " · annotated copy for the workshop"
            code = highlight(text, lexer, HtmlFormatter(nowrap=True))
            body.append(f'<div class="cap">{caption}</div><pre>{code}</pre>')
            plain.append(f"# ---- {name} ----\n{text}")
        panels.append(f'<div class="p{i}">{"".join(body)}</div>')
    display({"text/html": f'<style>{css}</style><div class="{uid}">{"".join(bar + panels)}</div>',
             "text/plain": "\n".join(plain)}, raw=True)
