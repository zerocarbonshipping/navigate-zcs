# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Shared machinery for scanning node instance attributes for node references,
used by the parser's reference resolution and the reachability analysis.
"""

import re
from typing import Any, Iterator

# a node reference in canonical deck form, e.g. Vessel("name");
# group 1 is the node type and group 3 the node name
NODE_REFERENCE_PATTERN = re.compile(r'^\s*(([A-Z][a-z]+)+)\(\s*"([^"]+)"\s*\)\s*$')

# node attributes that can never hold node references, skipped when the parser
# scans instance attributes to resolve references; every entry must name a real
# attribute (pinned by a unit test) so stale entries cannot accumulate silently
REFERENCE_SCAN_EXCLUDE = ('name', 'type', 'allow_dates_in_table', 'expectation', 'profile',
                          '_table', 'just_copied')


def get_attributes(instance: object, exclude: tuple = ()) -> Iterator[tuple[str, Any]]:
    """
    Extracts all attributes from the supplied instance except built-in attributes and attributes listed in 'exclude'.

    The instance's attribute dict is snapshotted so callers may reassign
    attributes while iterating.

    Parameters
    ----------
    instance
        Instance from which to extract attributes.
    exclude
        Tuple of strings with attributes to exclude from the list.

    Returns
    -------
    Generator of (name, attribute) pairs.
    """

    attributes = list(instance.__dict__.items())
    return ((name, attribute) for name, attribute in attributes
            if not (name.startswith('__') and name.endswith('__')) and name not in exclude)
