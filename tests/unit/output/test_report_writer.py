# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Resolution of Report property requests against the node registry."""

import logging

from navigate.core.enum_ import ReportReduceID
from navigate.core.nodes.vessel import Vessel
from navigate.output.report_writer import NodeReport, _prepare_export, export_properties_csv


def _report(attribute='Lifetime'):
    report = NodeReport()
    report.add_property(attribute, ReportReduceID.NONE)
    return report


class TestPrepareExport:

    def test_matched_name_exports(self):
        nodes = {'vessel': Vessel('vessel')}

        export = _prepare_export(nodes, {'vessel': _report()}, 'output', 'Vessels')

        assert set(export) == {'vessel'}
        assert export['vessel'][0] == ['Lifetime']

    def test_unmatched_name_warns_and_skips(self, caplog):
        nodes = {'vessel': Vessel('vessel')}

        with caplog.at_level(logging.WARNING):
            export = _prepare_export(nodes, {'ghost': _report()}, 'output', 'Vessels')

        assert export == {}
        assert "Report 'output': property request 'ghost' on sheet 'Vessels'" in caplog.text

    def test_csv_export_warns_with_its_report_name(self, caplog):
        nodes = {'vessel': Vessel('vessel')}

        with caplog.at_level(logging.WARNING):
            export_properties_csv('Vessel', nodes, {'ghost': _report()}, 'my_report', {})

        assert "Report 'my_report': property request 'ghost'" in caplog.text

    def test_unmatched_wildcard_warns_and_skips(self, caplog):
        nodes = {'vessel': Vessel('vessel')}

        with caplog.at_level(logging.WARNING):
            export = _prepare_export(nodes, {'z*': _report()}, 'output', 'Vessels')

        assert export == {}
        assert "property request 'z*'" in caplog.text
