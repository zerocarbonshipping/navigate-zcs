# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Excel and CSV writing engine behind the Report node.

The Report node collects which properties to extract per node type; write_report,
driven by the simulation manager, resolves those requests against the node profiles
and writes the workbook or CSV files.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

import openpyxl as xl

from navigate.core.enum_ import FileFormatID, ReportReduceID
from navigate.util import (
    dates_to_days,
    is_single_dict,
    is_tuple_dict,
    matching_keys,
    sum_by_first_key,
    sum_by_second_key,
    sum_dict_results,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    import numpy as np
    from openpyxl.worksheet.worksheet import Worksheet

    from navigate.core.node_report import NodeReport
    from navigate.core.nodes.report import Report
    from navigate.core.profiles._base_profile import _BaseProfile
    from navigate.simulation import SimulationManager
    from navigate.util.types_ import BoolArray, FloatArray

logger = logging.getLogger(__name__)

ROW_NODE = 1
ROW_ATTR = 2
ROW_KEY = 3
ROW_RESULT = 5


@dataclass
class CsvSheet:
    """Headers and data columns of one CSV report file, one column per header."""

    headers: list[str] = field(default_factory=list)
    columns: list[FloatArray | BoolArray] = field(default_factory=list)


class _Section(NamedTuple):
    """One node type's report requests together with the profiles they resolve to."""

    log_name: str
    sheet_title: str
    profiles: Mapping[str, _BaseProfile]
    requests: dict[str, NodeReport]


def write_report(
    report: Report,
    manager: SimulationManager,
    deck_directory: str,
    deck_name: str,
    dateline: np.ndarray,
) -> None:
    """
    Write one report node's requested properties to an XLSX or CSV file.

    Failures are contained per layer: a failed sheet is logged and skipped so the
    remaining sheets still export, and a failed save aborts only this report.

    The manager exports under its node name 'global', which is what the key of
    Report.add_property requests must match.

    Parameters
    ----------
    report
        Report node holding the collected export requests.
    manager
        Simulation manager providing the node collections.
    deck_directory
        Directory of the simulation deck, base for the report directory.
    deck_name
        Name of the simulation deck, used in the filenames.
    dateline
        Dates of the simulation timeline.
    """
    report_name = report.name

    if report.file_format == FileFormatID.XLSX:
        wb = xl.Workbook()

        def export_section(section: _Section) -> None:
            export_properties_xlsx(
                wb.create_sheet(title=section.sheet_title),
                section.profiles,
                section.requests,
                report_name,
            )

        def save(directory: str) -> None:
            write_xlsx_report(wb, directory, deck_name, report_name, dateline)

    else:
        sheets: dict[str, CsvSheet] = {}

        def export_section(section: _Section) -> None:
            export_properties_csv(
                section.sheet_title,
                section.profiles,
                section.requests,
                report_name,
                sheets,
            )

        def save(directory: str) -> None:
            write_csv_report(sheets, directory, deck_name, report_name, dateline)

    _export_and_save(report, manager, deck_directory, export_section, save)


def _export_and_save(
    report: Report,
    manager: SimulationManager,
    deck_directory: str,
    export_section: Callable[[_Section], None],
    save: Callable[[str], None],
) -> None:
    """
    Export each requested section, then save the report, containing failures per layer.

    Parameters
    ----------
    report
        Report node holding the collected export requests.
    manager
        Simulation manager providing the node collections.
    deck_directory
        Directory of the simulation deck, base for the report directory.
    export_section
        Exports one section into the format's pending output.
    save
        Writes the pending output into the given report directory.
    """
    report_name = report.name
    sheet_errors = 0

    for section in _sections(report, manager):
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


def _sections(report: Report, manager: SimulationManager) -> Iterator[_Section]:
    """
    Yield each section the report requests properties from, in sheet order.

    Parameters
    ----------
    report
        Report node holding the collected export requests.
    manager
        Simulation manager providing the node collections.

    Yields
    ------
    _Section
        Each section with at least one request, its profiles keyed by node name.
    """
    nodes = manager.nodes
    sections = (
        _Section(
            "manager", "Global", {manager.name: manager.profile}, report.manager_reports
        ),
        _Section(
            "fleets",
            "Fleets",
            {name: fleet.profile for name, fleet in nodes.fleets.items()},
            report.fleet_reports,
        ),
        _Section(
            "levies",
            "Levies",
            {name: levy.profile for name, levy in nodes.levies.items()},
            report.levy_reports,
        ),
        _Section(
            "plants",
            "Plants",
            {name: plant.profile for name, plant in nodes.plants.items()},
            report.plant_reports,
        ),
        _Section(
            "ports",
            "Ports",
            {name: port.profile for name, port in nodes.ports.items()},
            report.port_reports,
        ),
        _Section(
            "producers",
            "Producers",
            {name: producer.profile for name, producer in nodes.producers.items()},
            report.producer_reports,
        ),
        _Section(
            "regulations",
            "Regulations",
            {
                name: regulation.profile
                for name, regulation in nodes.regulations.items()
            },
            report.regulation_reports,
        ),
        _Section(
            "vessels",
            "Vessels",
            {name: vessel.profile for name, vessel in nodes.vessels.items()},
            report.vessel_reports,
        ),
    )

    for section in sections:
        if section.requests:
            yield section


def _ensure_report_directory(report: Report, deck_directory: str) -> str:
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
    str
        Path of the report directory.
    """
    if report.directory is not None:
        directory = os.path.join(deck_directory, report.directory)
    else:
        directory = deck_directory

    os.makedirs(directory, exist_ok=True)
    return directory


def write_xlsx_report(
    wb: xl.Workbook,
    directory: str,
    deck_name: str,
    report_name: str,
    dateline: np.ndarray,
) -> None:
    """
    Save the workbook, retrying alternative filenames while the target file is locked.

    Parameters
    ----------
    wb
        Workbook holding the exported sheets.
    directory
        Directory to save the file in.
    deck_name
        Name of the simulation deck, used in the filename.
    report_name
        Name of the Report node, used in the filename.
    dateline
        Dates of the simulation timeline.
    """
    base_path = os.path.join(directory, f"{deck_name}_{report_name}.xlsx")

    # delete default sheet if data has been
    # written, otherwise keep it to avoid error
    if len(wb.sheetnames) > 1:
        del wb["Sheet"]
        _export_date_time(wb, dateline)

    # save file with retry logic for locked files
    path = base_path
    max_attempts = 100

    for attempt in range(max_attempts):
        try:
            wb.save(path)
            if attempt > 0:
                logger.warning("Saved report to alternative filename: %s", path)
            break  # Success!
        except OSError:
            if attempt < max_attempts - 1:
                # Generate alternative filename
                path = _get_alternative_path(base_path, attempt + 1)
            else:
                # Final attempt failed, re-raise the error
                logger.error("Failed to save report after %s attempts", max_attempts)
                raise


def write_csv_report(
    sheets: dict[str, CsvSheet],
    directory: str,
    deck_name: str,
    report_name: str,
    dateline: np.ndarray,
) -> None:
    """
    Write one CSV per sheet, retrying alternative filenames while the target is locked.

    Parameters
    ----------
    sheets
        Sheets collected by export_properties_csv, keyed by sheet name.
    directory
        Directory to save the files in.
    deck_name
        Name of the simulation deck, used in the filenames.
    report_name
        Name of the Report node, used in the filenames.
    dateline
        Dates of the simulation timeline.
    """
    timeline = dates_to_days(dateline)

    for sheet_name, sheet in sheets.items():
        base_path = os.path.join(
            directory, f"{deck_name}_{report_name}_{sheet_name}.csv"
        )

        path = base_path
        max_attempts = 100

        for attempt in range(max_attempts):
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)

                    # Write headers
                    headers = ["Date", "Time (days)", *sheet.headers]
                    writer.writerow(headers)

                    # Write data rows
                    for i, date in enumerate(dateline):
                        row = [
                            str(date),  # Convert numpy datetime to string
                            timeline[i],
                        ]
                        # every column spans the full timeline, as profiles
                        # are initialized on it
                        row.extend([col[i] for col in sheet.columns])
                        writer.writerow(row)

                if attempt > 0:
                    logger.warning("Saved report to alternative filename: %s", path)
                break

            except OSError:
                if attempt < max_attempts - 1:
                    path = _get_alternative_path(base_path, attempt + 1)
                else:
                    logger.error(
                        "Failed to save report after %s attempts", max_attempts
                    )
                    raise


def export_properties_xlsx(
    ws: Worksheet,
    profiles: Mapping[str, _BaseProfile],
    requests: dict[str, NodeReport],
    report_name: str,
) -> None:
    """
    Write the requested properties of the given node profiles into a worksheet.

    Parameters
    ----------
    ws
        Worksheet to write into.
    profiles
        Profiles of all nodes of a certain type, keyed by node name.
    requests
        Node reports requested, keyed by node name or pattern.
    report_name
        Name of the Report node, used in log messages.
    """
    col = 3

    export = _prepare_export(profiles, requests, report_name, ws.title)

    for node_name, (attributes, getters, reductions) in export.items():
        properties = dict(
            _extract_properties(
                node_name,
                profiles[node_name],
                attributes,
                getters,
                reductions,
                report_name,
            )
        )

        col = _export_node(ws, node_name, properties, col)


def export_properties_csv(
    sheet_name: str,
    profiles: Mapping[str, _BaseProfile],
    requests: dict[str, NodeReport],
    report_name: str,
    sheets: dict[str, CsvSheet],
) -> None:
    """
    Flatten the node profiles' requested properties into one sheet, added to sheets.

    Parameters
    ----------
    sheet_name
        Sheet name to store the flattened data under.
    profiles
        Profiles of all nodes of a certain type, keyed by node name.
    requests
        Node reports requested, keyed by node name or pattern.
    report_name
        Name of the Report node, used in log messages.
    sheets
        Sheets keyed by sheet name, modified in-place; a sheet without data
        is not added.
    """
    export = _prepare_export(profiles, requests, report_name, sheet_name)

    sheet = CsvSheet()

    for node_name, (attributes, getters, reductions) in export.items():
        for attribute, property_ in _extract_properties(
            node_name,
            profiles[node_name],
            attributes,
            getters,
            reductions,
            report_name,
        ):
            _flatten_to_csv(sheet, node_name, attribute, property_)

    if sheet.headers:
        sheets[sheet_name] = sheet


def _extract_properties(
    node_name: str,
    profile: _BaseProfile,
    attributes: list[str],
    getters: list[str],
    reductions: list[ReportReduceID],
    report_name: str,
):
    """
    Yield (attribute, property) pairs from the node profile, with reductions applied.

    Parameters
    ----------
    node_name
        Name of the node, used in log messages.
    profile
        Profile of the node to read properties from.
    attributes
        Requested attribute names.
    getters
        Profile getter name per attribute.
    reductions
        Reduction to apply per attribute.
    report_name
        Name of the Report node, used in log messages.
    """
    for attribute, getter, reduce in zip(attributes, getters, reductions, strict=True):
        try:
            # the parser checked every getter against the profile class of its
            # command when it read the deck
            property_ = getattr(profile, getter)()

            if isinstance(property_, dict):
                property_ = _reduce_dict(property_, reduce)

            yield attribute, property_

        except Exception as e:
            logger.error(
                "Report '%s': Skipping property '%s' for node '%s': %s",
                report_name,
                attribute,
                node_name,
                e,
            )
            continue


def _reduce_dict(property_: dict, reduce: ReportReduceID) -> dict | np.ndarray:
    """
    Apply a report reduction to a dict-valued profile result.

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
        Profile result to reduce.
    reduce
        Reduction to apply.

    Returns
    -------
    dict | np.ndarray
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


def _get_alternative_path(base_path: str, counter: int) -> str:
    """
    Generate filename with counter suffix.

    Parameters
    ----------
    base_path
        Original file path (e.g., 'report.xlsx')
    counter
        Counter to append (e.g., 1 for 'report (1).xlsx')

    Returns
    -------
    Alternative path with counter suffix, e.g. '/path/to/file (1).xlsx'.
    """
    base, ext = os.path.splitext(base_path)
    return f"{base} ({counter}){ext}"


def _prepare_export(
    profiles: Mapping[str, _BaseProfile],
    requests: dict[str, NodeReport],
    report_name: str,
    sheet_name: str,
) -> dict:

    export = {}

    for key, report in requests.items():
        node_names = matching_keys(key, profiles)

        if not node_names:
            logger.warning(
                "Report '%s': property request '%s' on sheet '%s' does not match any "
                "node in the simulation; skipping.",
                report_name,
                key,
                sheet_name,
            )

            continue

        for node_name in node_names:
            if node_name not in export:
                export[node_name] = ([], [], [])

            export[node_name][0].extend(report.attributes)
            export[node_name][1].extend(report.getters)
            export[node_name][2].extend(report.reductions)

    return export


def _export_date_time(wb: xl.Workbook, dateline: np.ndarray) -> None:

    timeline = dates_to_days(dateline)

    for ws in wb.worksheets:
        ws.cell(row=ROW_NODE, column=1).value = "Date"
        ws.cell(row=ROW_NODE, column=2).value = "Time (days)"
        _export_array(ws, "", dateline.astype(datetime), 1)
        _export_array(ws, "", timeline, 2)


def _export_node(ws: Worksheet, node_name: str, properties: dict, col: int) -> int:

    first_col = col
    last_col = _write_properties(ws, properties, col) - 1

    # duplicate node name across each column header
    # if this is the first instance of the node export
    for col in range(first_col, last_col):
        ws.cell(row=ROW_NODE, column=col).value = node_name

    return last_col


def _write_properties(ws: Worksheet, properties: dict, col: int) -> int:

    for attribute, property_ in properties.items():
        try:
            if isinstance(property_, dict):
                col = _export_dict(ws, attribute, property_, col)

            else:
                col = _export_array(ws, attribute, property_, col)
        except Exception as e:
            logger.error("Skipping attribute '%s': %s", attribute, e)
            continue

    return col + 1


def _export_dict(ws: Worksheet, attribute: str, property_: dict, col: int) -> int:
    """
    Write a dict property into worksheet columns, one column per key.

    Each element of a tuple key goes in its own header row, from ROW_KEY down.

    Parameters
    ----------
    ws
        Worksheet to write into.
    attribute
        Name of the attribute, written as column header.
    property_
        Dict of arrays keyed by profile keys or tuples of them.
    col
        Column index to start writing at.

    Returns
    -------
    int
        The column index after the last column written.
    """
    first_col = col

    for key, value in property_.items():
        key_col = col

        if not isinstance(key, tuple):
            key = (key,)

        col = _export_array(ws, attribute, value, col)

        for k, key_ in enumerate(key):
            ws.cell(row=ROW_KEY + k, column=key_col).value = _format_header(key_)

    # duplicate attribute name across each column header
    last_col = col

    for col in range(first_col, last_col):
        ws.cell(row=ROW_ATTR, column=col).value = attribute

    return last_col


def _export_array(
    ws: Worksheet, attribute: str, property_: np.ndarray, col: int
) -> int:
    if attribute:
        ws.cell(row=ROW_ATTR, column=col).value = _format_header(attribute)

    return _export_time_series(ws, property_, col)


def _export_time_series(ws: Worksheet, series: np.ndarray, col: int) -> int:
    n = series.size

    # write time-series
    for i in range(n):
        ws.cell(row=ROW_RESULT + i, column=col).value = series[i]

    return col + 1


def _format_header(header):
    if isinstance(header, Enum):
        return header.name
    else:
        return header


def _flatten_to_csv(sheet: CsvSheet, node_name: str, attribute: str, property_) -> None:
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
        for key, value in property_.items():
            # Normalize key to tuple
            if not isinstance(key, tuple):
                key = (key,)

            key_str = ".".join(str(_format_header(k)) for k in key)
            sheet.headers.append(f"{node_name}.{attribute}.{key_str}")
            sheet.columns.append(value)

    else:
        sheet.headers.append(f"{node_name}.{attribute}")
        sheet.columns.append(property_)
