# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The results file page lists exactly the results each kind of the file holds.

docs/reference_manual/results_file.md is hand-written, so nothing but this test
keeps it from drifting from the result fields the results classes declare. The
kinds are named the way the results writer names them: "global" for the global
results, and the lowercased node type of every node type whose nodes hold
results. So a renamed node type, a new node type with results, an added, renamed
or removed result and a changed unit each fail here.
"""

from __future__ import annotations

import pytest

from helpers.reference_manual import RESULTS_PAGE, kind_column_values, results_tables
from navigate.core.node_registry import NODE_CLASS
from navigate.core.results import GlobalResults, result_units
from navigate.output.results_writer import GLOBAL_KIND


def _results_classes() -> dict[str, type]:
    classes: dict[str, type] = {GLOBAL_KIND: GlobalResults}

    for node_class in NODE_CLASS.values():
        # a node holds its results from construction, filled once the run starts
        results = getattr(node_class("probe"), "results", None)

        if results is not None:
            classes[node_class.type.lower()] = type(results)

    return classes


RESULTS_CLASS = _results_classes()
DOCUMENTED = results_tables()


# checks the Results section lists series of exactly the kinds the file holds.
# catches: a node type renamed, or a new node type with results, while the
# rows keep the old kinds.
def test_results_section_covers_every_kind():
    documented = set(DOCUMENTED)
    held = set(RESULTS_CLASS)

    assert documented == held, (
        f"{RESULTS_PAGE.name} '## Results' has drifted: kinds without a series "
        f"{sorted(held - documented)}; series of kinds the file never holds "
        f"{sorted(documented - held)}"
    )


# checks the kind column lists exactly the kinds the file holds.
# catches: the same drift in the column description under '## Table'.
def test_kind_column_lists_every_kind():
    documented = kind_column_values()
    held = set(RESULTS_CLASS)

    assert documented == held, (
        f"{RESULTS_PAGE.name} 'kind' column has drifted: missing "
        f"{sorted(held - documented)}; not held {sorted(documented - held)}"
    )


# compares the attributes listed for each kind, with their units, against the
# results its class declares, in both directions.
# catches: a result added without a row, a row left for a result renamed or
# removed, a unit changed on one side only, or a row naming the wrong kinds.
@pytest.mark.parametrize("kind", sorted(RESULTS_CLASS))
def test_kind_lists_its_results(kind):
    documented = DOCUMENTED.get(kind, {})
    declared = result_units(RESULTS_CLASS[kind])

    shared = documented.keys() & declared.keys()
    units = {name: (documented[name], declared[name]) for name in sorted(shared)}

    assert documented == declared, (
        f"{RESULTS_PAGE.name} kind '{kind}' has drifted: declared but unlisted "
        f"{sorted(declared.keys() - documented.keys())}; listed but undeclared "
        f"{sorted(documented.keys() - declared.keys())}; units differ (page, code) "
        f"{ {name: pair for name, pair in units.items() if pair[0] != pair[1]} }"
    )
