<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Navigate Syntax Highlighting

Syntax highlighting packages for the `.nav` / `.inc` DSL in three editors.

## VS Code

The extension is distributed as a `.vsix` bundle that the documentation build
packages from `syntax/vscode/`. Download it from the
[getting-started page](https://zerocarbonshipping.github.io/navigate-zcs/tutorials/getting_started.html)
of the documentation.

1. Open VS Code.
2. Run `Extensions: Install from VSIX...` from the command palette (`Ctrl+Shift+P`).
3. Select the downloaded `.vsix`.

Alternatively, from a terminal:

```bash
code --install-extension <path to the .vsix>
```

Reload the window. `.nav`, `.inc` and `.unc` files, and Horizon's `.hor` study
files, will be highlighted automatically.

To edit the grammar, change the files in `syntax/vscode/`, the extension's
source. To try a change, open a window with the extension loaded from the
folder:

```bash
code --extensionDevelopmentPath=<absolute path to syntax/vscode>
```

## PyCharm (and other JetBrains IDEs)

JetBrains IDEs read TextMate bundles via the bundled **TextMate Bundles** plugin (enabled by default).

1. Open `Settings` → `Editor` → `TextMate Bundles`.
2. Click `+` and select the `syntax/pycharm/Navigate.tmbundle` directory.
3. Click `Apply`.

The bundle declares `.nav`, `.inc`, and `.unc` as its file types, so highlighting applies automatically.

## Notepad++

Notepad++ uses User Defined Languages (UDL). Two UDLs are provided:

- `navigate_UDL.xml` / `navigate_UDL_dark.xml` — for `.nav` files.
- `include_UDL.xml` / `include_UDL_dark.xml` — for `.inc` files.

Pick the light or dark variant to match your theme.

1. In Notepad++, open `Language` → `User Defined Language` → `Define your language...`.
2. Click `Import...` and select the XML file(s) from `syntax/notepadpp/`.
3. Restart Notepad++.

The UDLs are pre-configured with the `.nav` and `.inc` file extensions, so files will be highlighted automatically when opened.
