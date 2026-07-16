# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from enum import Enum

import numpy as np
import pandas as pd

from navigate.core.expression import Expression
from navigate.core.id_ import CURVE, FORECAST, SURFACE, TIMETABLE
from navigate.core.node import Node
from navigate.core.scalar import Scalar
from navigate.output.unitdict import unitdict
from navigate.util import attribute_to_setter

LINE_BREAK_LENGTH = 50
SIGNIFICANT_DIGITS = 4

logger = logging.getLogger(__name__)


def process_list_tuple(value):
    """Process a sequence (list/tuple) into a formatted string."""
    processed = [str(process_value(v)) for v in value if v is not None]
    if not processed:
        return ""

    total_length = sum(len(str(s)) for s in processed)

    if total_length > LINE_BREAK_LENGTH or any(len(s) > LINE_BREAK_LENGTH for s in processed):
        return '[' + ',\n'.join(processed) + ']'
    return '[' + ', '.join(processed) + ']'


def handle_nums(x):
    if np.isinf(x) and x > 0:
        return "inf"
    elif np.isinf(x):
        return "-inf"
    else:
        return f"{round(x, SIGNIFICANT_DIGITS):g}"


def process_value(value):
    match value:
        case None:
            return None
        case float():
            return handle_nums(value)
        case Scalar():
            return handle_nums(value.get())
        case [*_]:
            return process_list_tuple(value)
        case Enum():
            return value.name
        case Expression():
            return process_value(value.get())
        case Node() as node:
            if node.is_variable():
                return f"{round(node.get(), SIGNIFICANT_DIGITS):g}"
            return str(node)
        case _:
            return str(value)


def write_sheet(writer, df, sheet_name):
    """Write a DataFrame to an Excel sheet with formatting."""
    if df.empty:
        return

    df = df.astype(str)
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    worksheet = writer.sheets[sheet_name]

    header_format = writer.book.add_format({
        'bold': True,
        'bg_color': '#D9E1F2',
        'border': 1
    })

    cell_format = writer.book.add_format({
        'text_wrap': True,
        'valign': 'top',
        'border': 1
    })

    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        max_length = max(df[value].str.len().max(), len(value))
        max_width = min(max_length + 2, 100)
        worksheet.set_column(col_num, col_num, max_width)

    for row_num in range(1, len(df) + 1):
        for col_num in range(len(df.columns)):
            worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], cell_format)

    worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)  # Apply filter to the first row
    worksheet.freeze_panes(1, 0)  # Freeze the first row in place


def process_table_data(node):
    """Process a table node into a list of rows for the Tables sheet."""

    rows = []

    # Handle 2D tables (curves/forecasts)
    if node.is_curve() or node.is_forecast():
        for idx, x in enumerate(node.get_x()):
            x_value = node.get_x_date()[idx] if node.is_forecast() else x
            y = node.calculate(x)

            rows.append({
                'Type': node.get_type(),
                'Name': node.get_name(),
                'X': f"{round(x_value, SIGNIFICANT_DIGITS):g}" if isinstance(x_value, float) else x_value,
                'Y': f"{round(y, SIGNIFICANT_DIGITS):g}" if isinstance(y, float) else y
            })

    # Handle 3D tables (surfaces/timetables)
    elif node.is_surface() or node.is_timetable():
        for x_idx, x in enumerate(node.get_x()):
            x_value = node.get_x_date()[x_idx] if node.is_timetable() else x

            for y in node.get_y():
                z = node.calculate(x, y)
                if isinstance(z, np.ndarray):
                    z = z[0]

                rows.append({
                    'Type': node.get_type(),
                    'Name': node.get_name(),
                    'X': f"{round(x_value, SIGNIFICANT_DIGITS):g}" if isinstance(x_value, float) else x_value,
                    'Y': f"{round(y, SIGNIFICANT_DIGITS):g}" if isinstance(y, float) else y,
                    'Z': f"{round(z, SIGNIFICANT_DIGITS):g}" if isinstance(z, float) else z
                })

    return rows


def collect_assumption_data(non_report_nodes, updates, start_date):
    """Collect assumption values and their history for export."""
    from navigate.parser._attributes import NODE_ATTRIBUTE_SECTIONS

    assumptions_data = []

    for node in non_report_nodes:
        node_type = node.get_type()
        if node_type in (CURVE, FORECAST, SURFACE, TIMETABLE):
            continue

        attr_section = NODE_ATTRIBUTE_SECTIONS.get(node_type, {})
        node_key = node.get_name()

        # fetch unit mapping for this node type once
        node_units = unitdict.get(node_type, {})

        for attr in attr_section:
            internal_attr = attribute_to_setter(attr, method='')
            if hasattr(node, internal_attr):
                current_value = process_value(getattr(node, internal_attr))
            elif hasattr(node, internal_attr.lstrip('_')):
                current_value = process_value(getattr(node, internal_attr.lstrip('_')))
            else:
                continue

            if current_value is None or pd.isna(current_value):
                continue

            param_name = attr.replace('get_', '')
            unit = node_units.get(param_name, None)

            node_updates = sorted(
                [u for u in updates.get(node_key, []) if u['attribute'] == attr],
                key=lambda x: x['date'] if x['date'] else pd.Timestamp.min
            )

            value_history = []

            if node_updates:
                initial_value = process_value(node_updates[0].get('old_value'))
                if initial_value is not None:
                    value_history.append((initial_value, start_date))

            for update in node_updates:
                value = process_value(update['value'])
                value_history.append((value, update['date']))

            if not value_history or value_history[-1][0] != current_value:
                value_history.append((current_value, start_date))

            for value, date in value_history:
                assumptions_data.append({
                    'Node': node_type,
                    'Name': node_key,
                    'Parameter': param_name,
                    'Assignment Date': date,
                    'Value': value,
                    'Unit': unit or ''
                })

    return assumptions_data


def export_assumptions(manager):
    """Export all model parameters and tables to an Excel file."""
    nodes = manager.get_parser()._get_all_nodes()
    updates = manager.get_parser().get_assumption_updates()
    non_report_nodes = [node for node in nodes if not node.is_report()]
    start_date = manager.get_parser().get_model_definition().get_start_date()

    assumptions_data = collect_assumption_data(non_report_nodes, updates, start_date)

    # Collect table data
    curves_forecasts_data = [
        row for node in non_report_nodes
        if (node.is_curve() or node.is_forecast())
        for row in process_table_data(node)
    ]

    surfaces_timetables_data = [
        row for node in non_report_nodes
        if (node.is_surface() or node.is_timetable())
        for row in process_table_data(node)
    ]

    # Write everything to Excel
    deck_name = manager.get_parser().get_deck_name()
    deck_dir = manager.get_parser().get_deck_directory()
    path = os.path.join(deck_dir, f"{deck_name}_assumptions.xlsx")

    with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
        write_sheet(writer, pd.DataFrame(assumptions_data), 'Assumptions')
        if curves_forecasts_data:
            write_sheet(writer, pd.DataFrame(curves_forecasts_data), 'Curves & Forecasts')
        if surfaces_timetables_data:
            write_sheet(writer, pd.DataFrame(surfaces_timetables_data), 'Surfaces & Timetables')

    logger.info(f"Assumptions exported to {path}")
