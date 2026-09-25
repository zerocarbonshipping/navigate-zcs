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

# '_figures' holds the scripts and source data that generate the workshop
# figures, not documentation. It carries a README.md, which myst_nb would
# otherwise pick up as an orphan document and warn about.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '_figures']

extensions = [
    # myst_nb supersedes myst_parser: it registers the same Markdown parser
    # plus .ipynb notebook support, so myst_parser is not listed separately.
    'myst_nb',
    'sphinx_design',
    'sphinx_copybutton',
]

source_suffix = {
    '.rst': 'restructuredtext',
}
# .md and .ipynb are left for myst_nb to register itself (as filetype
# "myst-nb"): pinning '.md' to 'markdown' here would block that registration,
# since Sphinx only lets an extension's source_suffix win over a value that
# isn't already user-set.

myst_heading_anchors = 4

myst_enable_extensions = [
    "dollarmath",
    "tasklist",
    "strikethrough",
    "colon_fence",
]

# Never execute notebooks during a docs build: workshop notebook 4 runs three
# reference scenarios of up to twenty minutes each, and the rest of the docs site
# never executes example code either (docs/tutorials/*.md show .nav/.inc
# listings as static text). Notebooks render with whatever output cells they
# were saved with (they now ship with saved output) rather than being
# re-run by Sphinx.
nb_execution_mode = 'off'

# strip interactive prompts so only the command is copied
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# -- Options for HTML output -------------------------------------------------

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']
html_js_files = ['colab-links.js', 'version-banner.js']

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
elif ref_name == "dev-workshop":
    # workshop preview at /workshop-preview/, until the workshop is merged into
    # dev; "-preview" makes the theme show its development-version banner
    version_match = "workshop-preview"
    release += "-preview"
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
