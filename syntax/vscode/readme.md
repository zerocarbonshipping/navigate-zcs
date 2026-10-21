<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# navigate-vscode-syntax

Syntax highlighting support for the **Navigate** language used by **Zero Carbon Shipping** models and simulations.

This extension adds basic language awareness to Visual Studio Code, making `.nav`, `.inc`, and `.unc` files easier to read, write, and review.

---

## Features

This extension provides:

- Syntax highlighting for Navigate source files
- Support for the following file extensions:
  - `.nav`
  - `.inc`
  - `.unc`
- Highlighting for:
  - Core Navigate keywords and section headers
  - The `Table` keyword
  - Numbers, strings, operators, and comments
  - Braces and brackets for improved readability

The goal is to mirror (and eventually exceed) the existing Notepad++ UDL highlighting in a modern VS Code workflow.

---

## Requirements

There are no external dependencies.

You only need:
- Visual Studio Code ≥ 1.80
- This extension installed

---

## Extension Settings

This extension does **not** currently contribute any custom VS Code settings.

All behavior is driven by the TextMate grammar and standard VS Code language configuration.

---

## Known Issues

- Syntax highlighting is purely lexical (TextMate-based); there is no semantic understanding of Navigate files.
- Complex multi-line constructs may not yet be highlighted perfectly.
- Folding and advanced language features (linting, validation, IntelliSense) are not implemented.

If you encounter issues or edge cases in real Navigate input decks, please open an issue with a minimal example.

---

## Release Notes

### 2.0.0

- Major rewrite as a VS Code language extension
- Ported and expanded syntax highlighting from the Notepad++ User Defined Language
- Support for `.nav`, `.inc`, and `.unc` files
- Improved keyword coverage and grammar structure

---

## Development Notes

This extension is implemented as a standard VS Code **language extension** using a TextMate grammar (`.tmLanguage.json`).

Contributions and refinements—especially around grammar accuracy and additional language features—are welcome.

---

## For more information

- [VS Code Language Extensions](https://code.visualstudio.com/api/language-extensions/overview)
- [Syntax Highlight Guide](https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide)
- [TextMate Grammar Format](https://macromates.com/manual/en/language_grammars)

---

**Enjoy working with Navigate in VS Code 🚢⚡**
