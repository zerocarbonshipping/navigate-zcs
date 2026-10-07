# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Resolution of Report property requests against the node registry.

Also covers the per-sheet error containment of write_report.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import numpy as np
import openpyxl as xl
import pytest

from navigate.core.enum_ import FuelTypeID, ReportReduceID
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.general_nodes.model_definition import ModelDefinition
from navigate.core.node_registry import GeneralNodes, Nodes
from navigate.core.node_report import NodeReport
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.report import Report
from navigate.core.nodes.vessel import Vessel
from navigate.core.profiles.global_profile import GlobalProfile
from navigate.core.profiles.vessel_profile import VesselProfile
from navigate.core.simulation_results import SimulationResults
from navigate.output import report_writer
from navigate.output.report_writer import (
    ROW_RESULT,
    CsvSheet,
    _extract_properties,
    _prepare_export,
    _reduce_dict,
    write_report,
)


def _node_report(attribute="Lifetime"):
    report = NodeReport()
    report.add_property(attribute, ReportReduceID.NONE)
    return report


class TestPrepareExport:
    def test_matched_name_exports(self):
        profiles = {"vessel": VesselProfile()}

        export = _prepare_export(
            profiles, {"vessel": _node_report()}, "output", "Vessels"
        )

        assert set(export) == {"vessel"}
        assert export["vessel"][0] == ["Lifetime"]

    def test_unmatched_name_warns_and_skips(self, caplog):
        profiles = {"vessel": VesselProfile()}

        with caplog.at_level(logging.WARNING):
            export = _prepare_export(
                profiles, {"ghost": _node_report()}, "output", "Vessels"
            )

        assert export == {}
        assert (
            "Report 'output': property request 'ghost' on sheet 'Vessels'"
            in caplog.text
        )


class TestReduceDict:
    """The appendix_ids.md ReportReduceID contract, applied to a dict property."""

    @pytest.fixture
    def tuple_dict(self):
        return {
            ("oil", "co2"): np.array([1.0]),
            ("oil", "ch4"): np.array([2.0]),
            ("lng", "co2"): np.array([4.0]),
        }

    @pytest.fixture
    def single_dict(self):
        return {"oil": np.array([1.0]), "lng": np.array([2.0])}

    def test_first_sums_over_the_first_element_keyed_by_the_second(self, tuple_dict):
        result = _reduce_dict(tuple_dict, ReportReduceID.FIRST)

        assert result.keys() == {"co2", "ch4"}
        np.testing.assert_array_equal(result["co2"], [5.0])
        np.testing.assert_array_equal(result["ch4"], [2.0])

    def test_second_sums_over_the_second_element_keyed_by_the_first(self, tuple_dict):
        result = _reduce_dict(tuple_dict, ReportReduceID.SECOND)

        assert result.keys() == {"oil", "lng"}
        np.testing.assert_array_equal(result["oil"], [3.0])
        np.testing.assert_array_equal(result["lng"], [4.0])

    def test_both_sums_over_both_elements_into_one_array(self, tuple_dict):
        result = _reduce_dict(tuple_dict, ReportReduceID.BOTH)

        np.testing.assert_array_equal(result, [7.0])

    def test_none_leaves_the_tuple_dict_unchanged(self, tuple_dict):
        assert _reduce_dict(tuple_dict, ReportReduceID.NONE) == tuple_dict

    def test_first_sums_a_single_key_dict_into_one_array(self, single_dict):
        result = _reduce_dict(single_dict, ReportReduceID.FIRST)

        np.testing.assert_array_equal(result, [3.0])

    def test_both_sums_a_single_key_dict_into_one_array(self, single_dict):
        result = _reduce_dict(single_dict, ReportReduceID.BOTH)

        np.testing.assert_array_equal(result, [3.0])

    def test_second_leaves_a_single_key_dict_unchanged(self, single_dict):
        assert _reduce_dict(single_dict, ReportReduceID.SECOND) == single_dict

    def test_none_leaves_a_single_key_dict_unchanged(self, single_dict):
        assert _reduce_dict(single_dict, ReportReduceID.NONE) == single_dict

    def test_empty_dict_is_unchanged(self):
        assert _reduce_dict({}, ReportReduceID.FIRST) == {}


class TestConverterEnergyReduction:
    """ConverterEnergy reduces over its (vessel fuel type, fuel) key like any tuple."""

    @staticmethod
    def _profile():
        def fuel(lower_heating_value):
            fuel_ = MagicMock()
            fuel_.fuel_type = FuelTypeID.OIL
            fuel_.liquid_market = False
            fuel_.lower_heating_value.get.return_value = lower_heating_value
            return fuel_

        profile = VesselProfile()
        profile.initialize(
            timeline=np.array([0.0]),
            emissions={},
            fuels={"fuel_a": fuel(2.0), "fuel_b": fuel(10.0)},
            emissions_lifetime=100.0,
        )

        # energy is mass times the lower heating value: OIL vessels burn 2 GJ
        # of fuel_a and 20 GJ of fuel_b, METHANOL vessels 6 GJ and 40 GJ
        profile.add_converter_mass(FuelTypeID.OIL, "fuel_a", 1.0)
        profile.add_converter_mass(FuelTypeID.OIL, "fuel_b", 2.0)
        profile.add_converter_mass(FuelTypeID.METHANOL, "fuel_a", 3.0)
        profile.add_converter_mass(FuelTypeID.METHANOL, "fuel_b", 4.0)

        return profile

    @classmethod
    def _reduced(cls, reduce):
        properties = dict(
            _extract_properties(
                "vessel",
                cls._profile(),
                ["ConverterEnergy"],
                ["get_converter_energy"],
                [reduce],
                "output",
            )
        )
        return properties["ConverterEnergy"]

    def test_first_sums_over_vessel_fuel_types_keyed_by_fuel(self):
        result = self._reduced(ReportReduceID.FIRST)

        assert result.keys() == {"fuel_a", "fuel_b"}
        np.testing.assert_array_equal(result["fuel_a"], [8.0])
        np.testing.assert_array_equal(result["fuel_b"], [60.0])

    def test_second_sums_over_fuels_keyed_by_vessel_fuel_type(self):
        result = self._reduced(ReportReduceID.SECOND)

        assert result.keys() == set(FuelTypeID)
        np.testing.assert_array_equal(result[FuelTypeID.OIL], [22.0])
        np.testing.assert_array_equal(result[FuelTypeID.METHANOL], [46.0])
        for fuel_type in set(FuelTypeID) - {FuelTypeID.OIL, FuelTypeID.METHANOL}:
            np.testing.assert_array_equal(result[fuel_type], [0.0])

    def test_both_sums_into_one_array(self):
        np.testing.assert_array_equal(self._reduced(ReportReduceID.BOTH), [68.0])


class TestWriteReportErrorContainment:
    @staticmethod
    def _report_and_results():
        report = Report("output")
        report.add_fleet_property("fleet", "Lifetime")
        report.add_vessel_property("vessel", "Lifetime")

        results = SimulationResults(
            dateline=np.array(["2030-01-01", "2031-01-01"], dtype="datetime64[D]"),
            profile=GlobalProfile(),
            nodes=Nodes(
                fleets={"fleet": Fleet("fleet")}, vessels={"vessel": Vessel("vessel")}
            ),
            general_nodes=GeneralNodes(
                bunker_options=BunkerOptions(), model_definition=ModelDefinition()
            ),
        )
        return report, results

    def test_failed_xlsx_sheet_is_skipped_and_the_report_still_saves(
        self, tmp_path, caplog, monkeypatch
    ):
        report, results = self._report_and_results()

        def fail_on_fleets(ws, profiles, requests, report_name):
            if ws.title == "Fleets":
                raise RuntimeError("boom")
            ws.cell(row=ROW_RESULT, column=3).value = "exported"

        monkeypatch.setattr(report_writer, "export_properties_xlsx", fail_on_fleets)
        with caplog.at_level(logging.WARNING):
            write_report(report, results, tmp_path, "deck")

        wb = xl.load_workbook(tmp_path / "deck_output.xlsx")
        assert wb["Vessels"].cell(row=ROW_RESULT, column=3).value == "exported"
        assert "Report 'output': Failed to export 'fleets': boom" in caplog.text
        assert "Report 'output': Completed with 1 sheet error(s)." in caplog.text

    def test_failed_csv_sheet_is_skipped_and_the_report_still_saves(
        self, tmp_path, caplog, monkeypatch
    ):
        report, results = self._report_and_results()
        report.set_file_format("CSV")

        def fail_on_fleets(sheet_name, profiles, requests, report_name, sheets):
            if sheet_name == "Fleets":
                raise RuntimeError("boom")
            sheets[sheet_name] = CsvSheet(
                headers=["marker"], columns=[np.array([1.0, 2.0])]
            )

        monkeypatch.setattr(report_writer, "export_properties_csv", fail_on_fleets)
        with caplog.at_level(logging.WARNING):
            write_report(report, results, tmp_path, "deck")

        assert (tmp_path / "deck_output_Vessels.csv").exists()
        assert not (tmp_path / "deck_output_Fleets.csv").exists()
        assert "Report 'output': Failed to export 'fleets': boom" in caplog.text
        assert "Report 'output': Completed with 1 sheet error(s)." in caplog.text
