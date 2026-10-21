# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Sphinx configuration for the Navigate documentation site.

All documentation content lives under docs/, so the site builds with a plain
sphinx-build.
"""

import json
import os
import tomllib
import zipfile
from pathlib import Path

# -- Project information -----------------------------------------------------

html_title = 'Navigate'
copyright = '2026, Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping'
author = 'Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping'

# single source of truth for the version so the docs and package can't drift
with (Path(__file__).resolve().parent.parent / 'pyproject.toml').open('rb') as _f:
    release = tomllib.load(_f)['project']['version']
version = release

# -- General configuration ---------------------------------------------------

language = 'en'
locale_dirs = []

exclude_patterns = ['_build', '_generated', 'Thumbs.db', '.DS_Store']

extensions = [
    'myst_parser',
    'sphinx_design',
    'sphinx_copybutton',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

myst_heading_anchors = 4

myst_enable_extensions = [
    "dollarmath",
    "tasklist",
    "strikethrough",
    "colon_fence",
]

# strip interactive prompts so only the command is copied
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# -- Options for HTML output -------------------------------------------------

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']
# the tutorial downloads; their contents land at the site root, so
# _generated/tutorials/tutorial_1.zip sits next to tutorials/tutorial_1.html
html_extra_path = ['_generated']

# The version-switcher dropdown matches this against the "version" fields in
# _static/switcher.json; the warning banner separately compares `release`
# against the "preferred" entry's version (both must be valid semver for the
# banner to be suppressed). On each release, update the preferred entry in
# switcher.json to the new version number.
ref_name = os.environ.get("GITHUB_REF_NAME", "main")
if ref_name == "dev":
    # staging docs; mark the build as a pre-release so the theme shows the
    # development-version warning banner
    version_match = "dev"
    release += "-dev"
elif ref_name in ("main", "HEAD"):
    version_match = release
else:
    version_match = ref_name.lstrip("vV")  # tag build, e.g. "v1.0.0" -> "1.0.0"

# top navbar lists the top-level sections (numpy-style); the logo links home.
html_theme_options = {
    "logo": {
        "text": "Navigate",
    },
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["version-switcher", "theme-switcher", "navbar-icon-links"],
    "navbar_align": "left",
    "header_links_before_dropdown": 5,
    "switcher": {
        "json_url": "https://zerocarbonshipping.github.io/navigate-zcs/_static/switcher.json",
        "version_match": version_match,
    },
    "show_version_warning_banner": True,
    "show_toc_level": 2,
    "use_edit_page_button": False,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/zerocarbonshipping/navigate-zcs",
            "icon": "fa-brands fa-github",
        },
    ],
}

# hide the left sidebar on the landing page for a clean home (numpy-style).
html_sidebars = {
    "index": [],
}


# -- Downloads ---------------------------------------------------------------

DOCS_DIR = Path(__file__).resolve().parent
TUTORIALS_DIR = DOCS_DIR / 'tutorials'
EXTENSION_DIR = DOCS_DIR.parent / 'syntax' / 'vscode'
DOWNLOADS_DIR = DOCS_DIR / '_generated' / 'tutorials'

# fixed timestamp so the archives do not change between builds
ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)

# Sphinx checks html_extra_path before any builder event, so the folder has
# to exist when this file is read
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def zip_tutorial_skeletons(app):
    """Zip each tutorial's starting files for the download on its page."""
    for tutorial in sorted(path for path in TUTORIALS_DIR.glob('tutorial_*') if path.is_dir()):
        files = sorted(path for path in tutorial.rglob('*') if path.suffix in ('.nav', '.inc'))
        with zipfile.ZipFile(DOWNLOADS_DIR / f'{tutorial.name}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                info = zipfile.ZipInfo(str(path.relative_to(TUTORIALS_DIR)), ZIP_DATE_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())


def vsix_manifest(package):
    """Return the `extension.vsixmanifest` that VS Code reads from a package.json."""
    tags = []
    for language in package['contributes']['languages']:
        tags += [language['id'], *language['aliases']]
        tags += [f'__ext_{extension.removeprefix(".")}' for extension in language['extensions']]

    tags = ','.join(dict.fromkeys([*tags, '__web_extension']))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
    <Metadata>
        <Identity Language="en-US" Id="{package['name']}" Version="{package['version']}" Publisher="{package['publisher']}" />
        <DisplayName>{package['displayName']}</DisplayName>
        <Description xml:space="preserve"></Description>
        <Tags>{tags}</Tags>
        <Categories>{','.join(package['categories'])}</Categories>
        <GalleryFlags>Public</GalleryFlags>
        <Properties>
            <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{package['engines']['vscode']}" />
            <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
            <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
            <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="ui,workspace,web" />
            <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
            <Property Id="Microsoft.VisualStudio.Code.EnabledApiProposals" Value="" />
            <Property Id="Microsoft.VisualStudio.Services.GitHubFlavoredMarkdown" Value="true" />
            <Property Id="Microsoft.VisualStudio.Services.Content.Pricing" Value="Free"/>
        </Properties>
    </Metadata>
    <Installation>
        <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
    </Installation>
    <Dependencies/>
    <Assets>
        <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
        <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/readme.md" Addressable="true" />
        <Asset Type="Microsoft.VisualStudio.Services.Content.Changelog" Path="extension/changelog.md" Addressable="true" />
    </Assets>
</PackageManifest>
"""


def zip_vscode_extension(app):
    """Package `syntax/vscode/` as the `.vsix` that the getting-started page offers."""
    package = json.loads((EXTENSION_DIR / 'package.json').read_text())
    vsix_path = DOWNLOADS_DIR / f"{package['name']}.vsix"
    content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension=".json" ContentType="application/json"/>
    <Default Extension=".md" ContentType="text/markdown"/>
    <Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
"""
    entries = {
        '[Content_Types].xml': content_types,
        'extension.vsixmanifest': vsix_manifest(package),
    }
    for path in sorted(path for path in EXTENSION_DIR.rglob('*') if path.is_file()):
        entries[f'extension/{path.relative_to(EXTENSION_DIR).as_posix()}'] = path.read_bytes()

    with zipfile.ZipFile(vsix_path, 'w') as archive:
        for name, content in entries.items():
            info = zipfile.ZipInfo(name, ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)


def setup(app):
    app.connect('builder-inited', zip_tutorial_skeletons)
    app.connect('builder-inited', zip_vscode_extension)
