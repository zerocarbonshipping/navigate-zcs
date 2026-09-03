# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Console summary of logged warnings."""
from collections import Counter

from navigate import logging_
from navigate.logging_ import print_warning_summary


class _FakeCountHandler:
    def __init__(self, counter):
        self.counter = counter


def test_warning_count_printed(monkeypatch, capsys):
    monkeypatch.setattr(logging_, '_COUNT_HANDLER', _FakeCountHandler(Counter({'WARNING': 2})))
    monkeypatch.setattr(logging_, '_LOG_FILE_NAME', 'deck.log')

    print_warning_summary()

    assert capsys.readouterr().out == "2 warning(s) logged - see 'deck.log'.\n"


def test_no_warnings_prints_nothing(monkeypatch, capsys):
    monkeypatch.setattr(logging_, '_COUNT_HANDLER', _FakeCountHandler(Counter()))
    monkeypatch.setattr(logging_, '_LOG_FILE_NAME', 'deck.log')

    print_warning_summary()

    assert capsys.readouterr().out == ''
