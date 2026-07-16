# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Sphinx configuration for the Navigate documentation site.

All documentation content lives under docs/, so the site builds with a plain
sphinx-build.
"""

import os
import tomllib
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

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

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
