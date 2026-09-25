# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The parser builds a Curve's table once the whole deck definition is read.

The interpolation and extrapolation settings apply wherever the definition
writes them, and a combination the table refuses is reported against the node.
The curve hangs under a top-level Emission so the prune keeps it.
"""

from __future__ import annotations

import pytest

from navigate.exceptions import AttributeAssignmentError

EMISSION = 'Emission "e" { GlobalWarmingPotential = Curve("c") }\n'
TABLE = "    Table = [\n        0 0\n        2 20\n    ]\n"


@pytest.mark.parametrize(
    "curve",
    [
        'Curve "c" {\n' + TABLE + "    Extrapolate = FLAT\n    Below = 5\n}\n",
        'Curve "c" {\n    Extrapolate = FLAT\n    Below = 5\n' + TABLE + "}\n",
        'Curve "c" {\n' + TABLE + '}\nCurve "c" {\n    Extrapolate = FLAT\n'
        "    Below = 5\n}\n",
    ],
    ids=["after_table", "before_table", "later_block"],
)
def test_the_extrapolation_applies_wherever_it_is_written(read_deck, curve):
    parser = read_deck(EMISSION + curve)

    # the flat value 5 below the table, not the linear extrapolation -10
    assert parser.nodes.curves["c"].get(-1.0) == pytest.approx(5.0)


def test_a_refused_setting_after_the_table_is_reported_against_the_node(read_deck):
    curve = 'Curve "c" {\n' + TABLE + "    Interpolate = PREVIOUS\n}\n"

    with pytest.raises(
        AttributeAssignmentError, match=r"Curve\(\"c\"\): 'Extrapolate'"
    ):
        read_deck(EMISSION + curve)
