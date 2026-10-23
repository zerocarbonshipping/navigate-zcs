# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Excel and CSV writing engine behind the Report node.

The Report node collects which properties to extract per node type; write_report
resolves those requests against the results in a run's SimulationResults and writes
the workbook or CSV files.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
import openpyxl as xl

from navigate.core.enum_ import FileFormatID, ReportAccumulationID, ReportReduceID
from navigate.core.node_report import GLOBAL_RESULTS_KEY, NodeReport
from navigate.core.results import per_step_results
from navigate.util import (
    dates_to_days,
    is_single_dict,
    is_tuple_dict,
    matching_keys,
    step_lengths,
    sum_by_first_key,
    sum_by_second_key,
    sum_dict_results,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping
    from pathlib import Path

    from openpyxl.worksheet.worksheet import Worksheet

    from navigate.core.nodes.report import Report
    from navigate.core.results._base_results import _BaseResults
    from navigate.output.simulation_results import SimulationResults
    from navigate.util.types_ import BoolArray, DateArray, FloatArray

logger = logging.getLogger(__name__)

# what a result, or a reduction of it, is: an array, or a dict of arrays
# keyed by result keys or pairs of them
type _ReportKeyPart = str | Enum
type _ReportKey = _ReportKeyPart | tuple[_ReportKeyPart, _ReportKeyPart]
type _ReportArray = FloatArray | BoolArray
type _ReportDict = dict[_ReportKey, FloatArray] | dict[_ReportKey, BoolArray]
type _ReportValue = _ReportArray | _ReportDict

# the header rows of a worksheet column; a tuple key fills _ROW_KEY and the row
# below, so the results start under both
_ROW_NODE = 1
_ROW_ATTRIBUTE = 2
_ROW_KEY = 3
_ROW_RESULT = 5

# the timeline columns leading every worksheet; the node columns follow them
_COLUMN_DATE = 1
_COLUMN_DAYS = 2


@dataclass
class _CsvSheet:
    """Headers and data columns of one CSV report file, one column per header."""

    headers: list[str] = field(default_factory=list)
    columns: list[_ReportArray] = field(default_factory=list)


class _Section(NamedTuple):
    """One node type's report requests together with the results they resolve to."""

    log_name: str
    sheet_title: str
    results_by_node: Mapping[str, _BaseResults]
    requests: dict[str, NodeReport]


def write_report(
    report: Report,
    results: SimulationResults,
    deck_directory: Path,
    deck_name: str,
) -> None:
    """
    Write one report node's requested properties to an XLSX or CSV file.

    Failures are contained per layer: a failed sheet is logged and skipped so the
    remaining sheets still export, and a failed save aborts only this report.

    Parameters
    ----------
    report
        Report node holding the collected export requests.
    results
        Results of the finished run.
    deck_directory
        Directory of the simulation deck, base for the report directory.
    deck_name
        Name of the simulation deck, used in the filenames.
    """
    report_name = report.name
    dateline = results.dateline
    stem = f"{deck_name}_{report_name}"

    if report.file_format == FileFormatID.XLSX:
        workbook = xl.Workbook()

        def export_section(section: _Section) -> None:
            worksheet = workbook.create_sheet(title=section.sheet_title)
            _export_xlsx_section(worksheet, section, report_name)

        def save(directory: Path) -> None:
            _save_xlsx(workbook, directory / f"{stem}.xlsx", dateline)

    else:
        sheets: dict[str, _CsvSheet] = {}

        def export_section(section: _Section) -> None:
            sheet = _export_csv_section(section, report_name)
            if sheet.headers:
                sheets[section.sheet_title] = sheet

        def save(directory: Path) -> None:
            _save_csv(sheets, directory, stem, dateline)

    _export_and_save(report, results, deck_directory, export_section, save)


def _export_and_save(
    report: Report,
    results: SimulationResults,
    deck_directory: Path,
    export_section: Callable[[_Section], None],
    save: Callable[[Path], None],
) -> None:
    """
    Export each requested section, then save the report, containing failures per layer.

    Parameters
    ----------
    report
        Report node holding the collected export requests.
    results
        Results of the finished run.
    deck_directory
        Directory of the simulation deck, base for the report directory.
    export_section
        Exports one section into the format's pending output.
    save
        Writes the pending output into the given report directory.
    """
    report_name = report.name
    sheet_errors = 0

    for section in _sections(report, results):
        try:
            export_section(section)
        except Exception as e:
            logger.error(
                "Report '%s': Failed to export '%s': %s",
                report_name,
                section.log_name,
                e,
            )
            sheet_errors += 1

    try:
        save(_ensure_report_directory(report, deck_directory))
    except Exception as e:
        logger.error("Report '%s': Failed to save file: %s", report_name, e)

    if sheet_errors:
        logger.warning(
            "Report '%s': Completed with %d sheet error(s).", report_name, sheet_errors
        )


def _sections(report: Report, results: SimulationResults) -> Iterator[_Section]:
    """
    Yield each section the report requests properties from, in sheet order.

    Parameters
    ----------
    report
        Report node holding the collected export requests.
    results
        Results of the finished run.

    Yields
    ------
    _Section
        Each section with at least one request, its node results keyed by node name.
    """
    nodes = results.nodes
    sections = (
        _Section(
            "global",
            "Global",
            {GLOBAL_RESULTS_KEY: results.global_results},
            report.global_reports,
        ),
        _Section(
            "fleets",
            "Fleets",
            {name: node.results for name, node in nodes.fleets.items()},
            report.fleet_reports,
        ),
        _Section(
            "levies",
            "Levies",
            {name: node.results for name, node in nodes.levies.items()},
            report.levy_reports,
        ),
        _Section(
            "plants",
            "Plants",
            {name: node.results for name, node in nodes.plants.items()},
            report.plant_reports,
        ),
        _Section(
            "ports",
            "Ports",
            {name: node.results for name, node in nodes.ports.items()},
            report.port_reports,
        ),
        _Section(
            "producers",
            "Producers",
            {name: node.results for name, node in nodes.producers.items()},
            report.producer_reports,
        ),
        _Section(
            "regulations",
            "Regulations",
            {name: node.results for name, node in nodes.regulations.items()},
            report.regulation_reports,
        ),
        _Section(
            "vessels",
            "Vessels",
            {name: node.results for name, node in nodes.vessels.items()},
            report.vessel_reports,
        ),
    )

    for section in sections:
        if section.requests:
            yield section


def _ensure_report_directory(report: Report, deck_directory: Path) -> Path:
    """
    Create the directory the report is saved in, if missing, and return it.

    Parameters
    ----------
    report
        Report node, whose directory is absolute or relative to the deck directory.
    deck_directory
        Directory of the simulation deck.

    Returns
    -------
    Path
        Path of the report directory.
    """
    if report.directory is not None:
        directory = deck_directory / report.directory
    else:
        directory = deck_directory

    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _save_xlsx(workbook: xl.Workbook, path: Path, dateline: DateArray) -> None:
    """
    Save the workbook, headed by the timeline, retrying while the file is locked.

    Parameters
    ----------
    workbook
        Workbook holding the exported sheets.
    path
        Path to save the workbook to.
    dateline
        Dates of the simulation timeline.
    """
    # a workbook cannot be saved without a sheet, so the default sheet stays
    # unless another one was written
    if len(workbook.sheetnames) > 1:
        del workbook["Sheet"]
        _export_timeline(workbook, dateline)

    _save_with_retries(path, workbook.save)


def _save_csv(
    sheets: dict[str, _CsvSheet], directory: Path, stem: str, dateline: DateArray
) -> None:
    """
    Write one CSV per sheet, retrying while a file is locked.

    Parameters
    ----------
    sheets
        Sheets collected by _export_csv_section, keyed by sheet name.
    directory
        Directory to save the files in.
    stem
        Start of each filename, which the sheet name completes.
    dateline
        Dates of the simulation timeline.
    """
    for sheet_name, sheet in sheets.items():
        path = directory / f"{stem}_{sheet_name}.csv"
        save = partial(_write_csv, sheet=sheet, dateline=dateline)
        _save_with_retries(path, save)


def _write_csv(path: Path, sheet: _CsvSheet, dateline: DateArray) -> None:
    """Write a sheet to a CSV file, one row per date."""
    days = dates_to_days(dateline)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Time (days)", *sheet.headers])

        # every column spans the full timeline, as results are initialized on it
        for i, date in enumerate(dateline):
            values = [column[i] for column in sheet.columns]
            writer.writerow([str(date), days[i], *values])


def _save_with_retries(path: Path, save: Callable[[Path], None]) -> None:
    """Save to the path, or to the first alternative path while the file is locked."""
    max_attempts = 100

    for attempt in range(max_attempts):
        target = _alternative_path(path, attempt) if attempt else path

        try:
            save(target)
        except OSError:
            if attempt < max_attempts - 1:
                continue

            logger.error("Failed to save report after %s attempts", max_attempts)
            raise

        if attempt:
            logger.warning("Saved report to alternative filename: %s", target)

        return


def _alternative_path(path: Path, counter: int) -> Path:
    """Return the path with a counter before its suffix, as in 'report (1).xlsx'."""
    return path.with_name(f"{path.stem} ({counter}){path.suffix}")


def _export_xlsx_section(
    worksheet: Worksheet, section: _Section, report_name: str
) -> None:
    """
    Write the requested properties of a section's nodes into a worksheet.

    Parameters
    ----------
    worksheet
        Worksheet to write into.
    section
        Section holding the requests and the results of its nodes.
    report_name
        Name of the Report node, used in log messages.
    """
    column = _COLUMN_DAYS + 1

    for node_name, requested in _requests_by_node(section, report_name).items():
        node_results = section.results_by_node[node_name]
        extracted = _extract_properties(node_name, node_results, requested, report_name)

        # an attribute that several requests name is written once per node
        properties = dict(extracted)
        column = _export_node(worksheet, node_name, properties, column)


def _export_node(
    worksheet: Worksheet,
    node_name: str,
    properties: dict[str, _ReportValue],
    first_column: int,
) -> int:
    next_column = _export_properties(worksheet, properties, first_column)

    # the node name heads each column its properties fill
    for column in range(first_column, next_column):
        worksheet.cell(row=_ROW_NODE, column=column).value = node_name

    return next_column


def _export_properties(
    worksheet: Worksheet, properties: dict[str, _ReportValue], column: int
) -> int:
    for attribute, property_ in properties.items():
        try:
            if isinstance(property_, dict):
                column = _export_dict(worksheet, attribute, property_, column)
            else:
                column = _export_array(worksheet, attribute, property_, column)
        except Exception as e:
            logger.error("Skipping attribute '%s': %s", attribute, e)

    return column


def _export_dict(
    worksheet: Worksheet, attribute: str, property_: _ReportDict, column: int
) -> int:
    """
    Write a dict property into worksheet columns, one column per key.

    Each element of a tuple key goes in its own header row, from _ROW_KEY down.

    Parameters
    ----------
    worksheet
        Worksheet to write into.
    attribute
        Name of the attribute, written as column header.
    property_
        Dict of arrays keyed by result keys or tuples of them.
    column
        Column index to start writing at.

    Returns
    -------
    int
        The column index after the last column written.
    """
    for key, values in property_.items():
        for row, header in enumerate(_key_headers(key), start=_ROW_KEY):
            worksheet.cell(row=row, column=column).value = header

        column = _export_array(worksheet, attribute, values, column)

    return column


def _export_array(
    worksheet: Worksheet, attribute: str, property_: _ReportArray, column: int
) -> int:
    worksheet.cell(row=_ROW_ATTRIBUTE, column=column).value = attribute
    return _export_time_series(worksheet, property_, column)


def _export_timeline(workbook: xl.Workbook, dateline: DateArray) -> None:
    """Head every worksheet with the dates and the days since the first date."""
    dates = dateline.astype(datetime)
    days = dates_to_days(dateline)

    for worksheet in workbook.worksheets:
        worksheet.cell(row=_ROW_NODE, column=_COLUMN_DATE).value = "Date"
        worksheet.cell(row=_ROW_NODE, column=_COLUMN_DAYS).value = "Time (days)"
        _export_time_series(worksheet, dates, _COLUMN_DATE)
        _export_time_series(worksheet, days, _COLUMN_DAYS)


def _export_time_series(worksheet: Worksheet, series: _ReportArray, column: int) -> int:
    for i, value in enumerate(series):
        worksheet.cell(row=_ROW_RESULT + i, column=column).value = value

    return column + 1


def _export_csv_section(section: _Section, report_name: str) -> _CsvSheet:
    """
    Flatten the requested properties of a section's nodes into one sheet.

    Parameters
    ----------
    section
        Section holding the requests and the results of its nodes.
    report_name
        Name of the Report node, used in log messages.

    Returns
    -------
    _CsvSheet
        Sheet holding a header and a column per array of each property.
    """
    sheet = _CsvSheet()

    for node_name, requested in _requests_by_node(section, report_name).items():
        node_results = section.results_by_node[node_name]
        extracted = _extract_properties(node_name, node_results, requested, report_name)

        for attribute, property_ in extracted:
            _export_csv_property(sheet, node_name, attribute, property_)

    return sheet


def _export_csv_property(
    sheet: _CsvSheet, node_name: str, attribute: str, property_: _ReportValue
) -> None:
    """
    Flatten a property into CSV headers and columns, one column per array.

    Parameters
    ----------
    sheet
        Sheet to append the headers and columns to, modified in-place.
    node_name
        Name of the node.
    attribute
        Name of the attribute.
    property_
        The property to flatten, an array or a dict of arrays.
    """
    if isinstance(property_, dict):
        for key, values in property_.items():
            header = ".".join([node_name, attribute, *_key_headers(key)])
            sheet.headers.append(header)
            sheet.columns.append(values)
    else:
        sheet.headers.append(f"{node_name}.{attribute}")
        sheet.columns.append(property_)


def _requests_by_node(section: _Section, report_name: str) -> dict[str, NodeReport]:
    """Merge the section's requests per node they match, in the order first matched."""
    requests_by_node: dict[str, NodeReport] = {}

    for key, requested in section.requests.items():
        node_names = matching_keys(key, section.results_by_node)

        if not node_names:
            logger.warning(
                "Report '%s': property request '%s' on sheet '%s' does not match any "
                "node in the simulation; skipping.",
                report_name,
                key,
                section.sheet_title,
            )
            continue

        for node_name in node_names:
            merged = requests_by_node.setdefault(node_name, NodeReport())
            merged.attributes.extend(requested.attributes)
            merged.results.extend(requested.results)
            merged.reductions.extend(requested.reductions)
            merged.accumulations.extend(requested.accumulations)

    return requests_by_node


def _extract_properties(
    node_name: str,
    node_results: _BaseResults,
    requested: NodeReport,
    report_name: str,
) -> Iterator[tuple[str, _ReportValue]]:
    """
    Yield (attribute, property) pairs from the node's results, reduced and accumulated.

    Parameters
    ----------
    node_name
        Name of the node, used in log messages.
    node_results
        Results of the node to read properties from.
    requested
        The attribute names, their result names, and the reduction and
        accumulation to apply to each.
    report_name
        Name of the Report node, used in log messages.

    Yields
    ------
    tuple[str, _ReportValue]
        Each attribute whose result could be read, with its reduced result.
    """
    per_step = per_step_results(type(node_results))
    requests = zip(
        requested.attributes,
        requested.results,
        requested.reductions,
        requested.accumulations,
        strict=True,
    )

    for attribute, result, reduce, accumulate in requests:
        try:
            # the parser checked every result name against the results class of
            # its command when it read the deck, and every result is a
            # report value
            property_: _ReportValue = getattr(node_results, result)

            if isinstance(property_, dict):
                property_ = _reduce_dict(property_, reduce)

            if accumulate is ReportAccumulationID.CUMULATIVE:
                property_ = _accumulate(property_, node_results, result in per_step)
        except Exception as e:
            logger.error(
                "Report '%s': Skipping property '%s' for node '%s': %s",
                report_name,
                attribute,
                node_name,
                e,
            )
            continue

        yield attribute, property_


def _reduce_dict(property_: dict[Any, Any], reduce: ReportReduceID) -> _ReportValue:
    """
    Apply a report reduction to a dict-valued result.

    A tuple-keyed dict is collapsed by summing over the element(s) reduce
    names, keyed by whichever element remains: FIRST sums over the first
    element, keying the result by the second; SECOND sums over the second,
    keying it by the first; BOTH sums over both elements into a single
    array; NONE leaves the dict as-is. A single-key dict has only one
    element to sum over, so FIRST and BOTH collapse it into a single array
    and SECOND and NONE leave it unchanged. An empty dict is returned
    unchanged.

    Parameters
    ----------
    property_
        Result to reduce.
    reduce
        Reduction to apply.

    Returns
    -------
    _ReportValue
        Reduced result, in the form implied by reduce.
    """
    if not property_:
        return property_

    if is_single_dict(property_):
        if reduce in (ReportReduceID.FIRST, ReportReduceID.BOTH):
            return sum_dict_results(property_)

        return property_

    if is_tuple_dict(property_):
        if reduce is ReportReduceID.FIRST:
            return sum_by_second_key(property_)

        if reduce is ReportReduceID.SECOND:
            return sum_by_first_key(property_)

        if reduce is ReportReduceID.BOTH:
            return sum_dict_results(property_)

    return property_


def _accumulate(
    property_: _ReportValue, node_results: _BaseResults, per_step: bool
) -> _ReportValue:
    """Sum a reduced result over the time steps up to and including each date."""
    # a rate covers the step ending at its date, the first a year long as in the
    # run; a count per time step is already one step's worth
    weight = 1.0 if per_step else step_lengths(node_results.context.timeline)

    if isinstance(property_, dict):
        return {key: np.cumsum(values * weight) for key, values in property_.items()}

    return np.cumsum(property_ * weight)


def _key_headers(key: _ReportKey) -> list[str]:
    """Return a header per element of a result key, an enum member by its name."""
    parts = key if isinstance(key, tuple) else (key,)
    return [part.name if isinstance(part, Enum) else part for part in parts]
