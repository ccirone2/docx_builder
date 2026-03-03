"""
excel_plan.py — Pure logic layer for Excel sheet planning.

Computes sheet layouts and cell instructions as data structures.
No xlwings dependency — fully testable and Pyodide-compatible.

The Data Entry sheet uses Single-Column Notation (SCN) in column A:
  [Section]  — group headers
  ;; Label   — field label comments
  key:       — field key declarations
  (value)    — user-entered data

Tables use separate sheets with SCN dict-list notation:
  +field_key / key: / value per column per row.

See also:
  - engine/scn.py — SCN parser and serializer
  - excel_control.py — Control sheet layout planning
  - excel_writer.py — xlwings adapter layer
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.config import (
    HEADER_COLOR,
    HEADER_FONT_COLOR,
    SCN_COMMENT_PREFIX,
    SHEET_DATA_ENTRY,
)
from engine.schema_loader import FieldDef, Schema

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CellInstruction:
    """Instruction to write a single cell with formatting."""

    sheet: str
    row: int
    col: int  # 1-based
    value: Any
    bold: bool = False
    bg_color: str = ""
    font_color: str = ""
    number_format: str = ""
    is_header: bool = False
    note: str = ""
    field_key: str = ""  # FieldDef.key for data-entry value cells


@dataclass
class SheetPlan:
    """Plan for which sheets to create and what cells to write."""

    sheets: list[str]
    instructions: list[CellInstruction]


# ---------------------------------------------------------------------------
# Sheet name helpers
# ---------------------------------------------------------------------------

_MAX_SHEET_NAME = 31  # Excel maximum
_ILLEGAL_SHEET_CHARS = str.maketrans({c: "-" for c in ":/\\?*[]"})


def _truncate_sheet_name(name: str) -> str:
    """Sanitize and truncate a sheet name for Excel.

    Replaces characters that Excel forbids in sheet names
    (: / \\ ? * [ ]) with hyphens, then trims to 31 characters.

    Args:
        name: Proposed sheet name.

    Returns:
        Sanitized name trimmed to 31 characters.
    """
    return name.translate(_ILLEGAL_SHEET_CHARS)[:_MAX_SHEET_NAME]


def _table_sheet_name(field_label: str) -> str:
    """Generate a sheet name for a table field."""
    return _truncate_sheet_name(field_label)


# ---------------------------------------------------------------------------
# Data Entry sheet — single-column SCN layout
# ---------------------------------------------------------------------------


def plan_data_entry(schema: Schema) -> tuple[list[CellInstruction], int]:
    """Plan the Data Entry sheet with SCN layout in column A.

    Produces key declarations and empty value cells for each field,
    grouped under [Section] headers. All in column 1.

    Args:
        schema: The active schema definition.

    Returns:
        Tuple of (instructions list, next_row after all content).
    """
    instrs: list[CellInstruction] = []
    row = 1

    for group in schema.all_groups:
        non_table = [f for f in group.fields if not f.is_table]
        if not non_table:
            continue

        # [Group Name] — section header
        instrs.append(
            CellInstruction(
                sheet=SHEET_DATA_ENTRY,
                row=row,
                col=1,
                value=f"[{group.name}]",
                bold=True,
                bg_color=HEADER_COLOR,
                font_color=HEADER_FONT_COLOR,
                is_header=True,
            )
        )
        row += 1

        for field in non_table:
            if field.is_compound:
                instrs.extend(_compound_field_rows(field, row))
                # 2 rows per sub-field: key + value
                row += len(field.sub_fields or []) * 2
            else:
                instrs.extend(_simple_field_rows(field, row))
                # 2 rows: key + value
                row += 2

        # Blank row between groups
        row += 1

    return instrs, row


def _simple_field_rows(field: FieldDef, start_row: int) -> list[CellInstruction]:
    """Generate SCN rows for a simple (non-compound, non-table) field.

    Produces 2 rows: key declaration, value cell.
    """
    return [
        # field_key:
        CellInstruction(
            sheet=SHEET_DATA_ENTRY,
            row=start_row,
            col=1,
            value=f"{field.key}:",
            bold=True,
        ),
        # (empty value cell)
        CellInstruction(
            sheet=SHEET_DATA_ENTRY,
            row=start_row + 1,
            col=1,
            value="",
            field_key=field.key,
        ),
    ]


def _compound_field_rows(field: FieldDef, start_row: int) -> list[CellInstruction]:
    """Generate SCN rows for a compound field and its sub-fields.

    Produces 2 rows per sub-field: key declaration, value cell.
    """
    instrs: list[CellInstruction] = []
    row = start_row

    for sf in field.sub_fields or []:
        dotted_key = f"{field.key}.{sf.key}"

        # parent_key.sub_key:
        instrs.append(
            CellInstruction(
                sheet=SHEET_DATA_ENTRY,
                row=row,
                col=1,
                value=f"{dotted_key}:",
                bold=True,
            )
        )
        # (empty value cell)
        instrs.append(
            CellInstruction(
                sheet=SHEET_DATA_ENTRY,
                row=row + 1,
                col=1,
                value="",
                field_key=dotted_key,
            )
        )
        row += 2

    return instrs


# ---------------------------------------------------------------------------
# Table sheets — SCN dict-list layout
# ---------------------------------------------------------------------------


def plan_table_layout(field: FieldDef, sheet_name: str) -> list[CellInstruction]:
    """Plan a table sheet using SCN dict-list notation.

    Each default row becomes a +field_key entry with key:/value pairs
    for each column. If no default rows, emits one empty template row.

    Args:
        field: A table-type FieldDef.
        sheet_name: Target sheet name.

    Returns:
        List of CellInstruction for the table sheet.
    """
    columns = field.columns or []
    instrs: list[CellInstruction] = []
    row = 1

    # Comment header describing the table
    col_labels = ", ".join(c["label"] for c in columns)
    instrs.append(
        CellInstruction(
            sheet=sheet_name,
            row=row,
            col=1,
            value=f"{SCN_COMMENT_PREFIX} {field.label}: {col_labels}",
            bold=True,
            is_header=True,
        )
    )
    row += 1

    default_rows = field.default_rows or []
    if not default_rows:
        # One empty template row
        default_rows = [{}]

    for row_data in default_rows:
        instrs.append(
            CellInstruction(
                sheet=sheet_name,
                row=row,
                col=1,
                value=f"+{field.key}",
            )
        )
        row += 1

        for col_def in columns:
            instrs.append(
                CellInstruction(
                    sheet=sheet_name,
                    row=row,
                    col=1,
                    value=f"{col_def['key']}:",
                    bold=True,
                )
            )
            row += 1

            val = row_data.get(col_def["key"], "")
            instrs.append(
                CellInstruction(
                    sheet=sheet_name,
                    row=row,
                    col=1,
                    value=str(val) if val else "",
                )
            )
            row += 1

    return instrs


# ---------------------------------------------------------------------------
# Top-level planner
# ---------------------------------------------------------------------------


def plan_sheets(schema: Schema) -> SheetPlan:
    """Plan all data entry and table sheets for a schema.

    Creates a single "Data Entry" sheet with SCN layout for all
    non-table fields, plus separate sheets for each table field.

    Args:
        schema: The active schema definition.

    Returns:
        SheetPlan with sheet names and cell instructions.
    """
    sheets: list[str] = [SHEET_DATA_ENTRY]
    instructions: list[CellInstruction] = []

    # Data Entry sheet
    entry_instrs, _ = plan_data_entry(schema)
    instructions.extend(entry_instrs)

    # Table sheets
    for group in schema.all_groups:
        for f in group.fields:
            if f.is_table:
                table_sheet = _table_sheet_name(f.label)
                sheets.append(table_sheet)
                instructions.extend(plan_table_layout(f, table_sheet))

    return SheetPlan(sheets=sheets, instructions=instructions)
