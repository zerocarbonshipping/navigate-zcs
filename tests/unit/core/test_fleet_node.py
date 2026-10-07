# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Fleet node's attribute setters."""

from __future__ import annotations

import logging

from navigate.core.nodes.fleet import Fleet


class TestSetInitialSplitRescaleLogging:
    """`set_initial_split` warns only once the rescale exceeds 1%."""

    def test_rescale_beyond_one_percent_logs_a_warning(self, caplog):
        fleet = Fleet("f")

        with caplog.at_level(logging.WARNING):
            fleet.set_initial_split([0.4, 0.4])

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert (
            "'InitialSplit' is rescaled proportionally to sum to 1."
            in warnings[0].getMessage()
        )

    def test_rescale_within_one_percent_logs_nothing(self, caplog):
        fleet = Fleet("f")

        with caplog.at_level(logging.WARNING):
            fleet.set_initial_split([0.5, 0.505])

        assert caplog.records == []
