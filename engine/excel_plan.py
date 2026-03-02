"""
excel_plan.py — Pure logic layer for Excel sheet planning.

Computes sheet layouts, cell positions, dropdown lists, and formatting
instructions as data structures. No xlwings dependency — fully testable
and Pyodide-compatible.

Split from excel_builder.py for module size. See also:
  - excel_control.py — Control sheet layout planning
  - excel_writer.py — xlwings adapter layer
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Any

from engine.config import (
    HEADER_COLOR,
    HEADER_FONT_COLOR,
    OPTIONAL_BG_COLOR,
    REQUIRED_INDICATOR_COLOR,
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
    merge_cols: int = 1
    row_height: int | None = None
    dropdown_choices: list[str] | None = None
    is_header: bool = False
    note: str = ""
    field_key: str = ""  # FieldDef.key for data-entry value cells


@dataclass
class SheetPlan:
    """Plan for which sheets to create and what cells to write."""

    sheets: list[str]
    instructions: list[CellInstruction]
    field_locations: dict[str, tuple[str, int, int]] = dc_field(default_factory=dict)
    # Maps field_key → (sheet_name, row, value_col) for O(1) reads


@dataclass
class TablePlan:
    """Plan for a table-type field's sheet layout."""

    sheet: str
    headers: list[CellInstruction]
    default_rows: list[list[CellInstruction]]


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


def _group_sheet_name(group_name: str, section: str) -> str:
    """Generate a sheet name for a field group."""
    return _truncate_sheet_name(group_name)


def _table_sheet_name(field_label: str) -> str:
    """Generate a sheet name for a table field."""
    return _truncate_sheet_name(field_label)


# ---------------------------------------------------------------------------
# Pure logic layer — plan_sheets
# ---------------------------------------------------------------------------


def plan_sheets(schema: Schema) -> SheetPlan:
    """Determine which sheets to create and compute all cell instructions.

    Args:
        schema: The active schema definition.

    Returns:
        SheetPlan with sheet names, cell instructions, and field_locations index.
    """
    sheets: list[str] = []
    instructions: list[CellInstruction] = []

    # Core groups
    for group in schema.core_groups:
        has_table = any(f.is_table for f in group.fields)
        non_table_fields = [f for f in group.fields if not f.is_table]

        # Group sheet for non-table fields
        if non_table_fields:
            sheet_name = _group_sheet_name(group.name, "core")
            sheets.append(sheet_name)
            group_instrs = plan_group_layout(group.name, non_table_fields, sheet_name)
            instructions.extend(group_instrs)

        # Separate sheet for each table field
        if has_table:
            for f in group.fields:
                if f.is_table:
                    table_sheet = _table_sheet_name(f.label)
                    sheets.append(table_sheet)
                    tp = plan_table_layout(f, table_sheet)
                    instructions.extend(tp.headers)
                    for row in tp.default_rows:
                        instructions.extend(row)

    # Optional groups
    for group in schema.optional_groups:
        has_table = any(f.is_table for f in group.fields)
        non_table_fields = [f for f in group.fields if not f.is_table]

        if non_table_fields:
            sheet_name = _group_sheet_name(group.name, "optional")
            sheets.append(sheet_name)
            group_instrs = plan_group_layout(group.name, non_table_fields, sheet_name)
            instructions.extend(group_instrs)

        if has_table:
            for f in group.fields:
                if f.is_table:
                    table_sheet = _table_sheet_name(f.label)
                    sheets.append(table_sheet)
                    tp = plan_table_layout(f, table_sheet)
                    instructions.extend(tp.headers)
                    for row in tp.default_rows:
                        instructions.extend(row)

    # Build field→location index from instructions
    locations: dict[str, tuple[str, int, int]] = {}
    for instr in instructions:
        if instr.field_key:
            locations[instr.field_key] = (instr.sheet, instr.row, instr.col)

    return SheetPlan(sheets=sheets, instructions=instructions, field_locations=locations)


# ---------------------------------------------------------------------------
# Pure logic layer — plan_group_layout
# ---------------------------------------------------------------------------


def plan_group_layout(
    group_name: str,
    fields: list[FieldDef],
    sheet_name: str,
    start_row: int = 2,
) -> list[CellInstruction]:
    """Compute cell instructions for a group of fields.

    Args:
        group_name: The group name (used for header).
        fields: List of FieldDef in this group.
        sheet_name: Target sheet name.
        start_row: Starting row (default 2, row 1 reserved for sheet title).

    Returns:
        List of CellInstruction for all fields in the group.
    """
    instructions: list[CellInstruction] = []
    row = start_row

    # Group header
    instructions.append(
        CellInstruction(
            sheet=sheet_name,
            row=1,
            col=1,
            value=group_name,
            bold=True,
            bg_color=HEADER_COLOR,
            font_color=HEADER_FONT_COLOR,
            merge_cols=5,
            is_header=True,
        )
    )

    for field in fields:
        if field.is_compound:
            # Compound field: sub-header row then indented sub-fields
            instructions.append(
                CellInstruction(
                    sheet=sheet_name,
                    row=row,
                    col=1,
                    value=field.label,
                    bold=True,
                    bg_color=OPTIONAL_BG_COLOR,
                    merge_cols=5,
                    is_header=True,
                )
            )
            row += 1

            for sf in field.sub_fields or []:
                instructions.extend(_field_row_instructions(sf, sheet_name, row, indent=True))
                row += 1
        else:
            instructions.extend(_field_row_instructions(field, sheet_name, row))
            row += 1

    return instructions


def _field_row_instructions(
    field: FieldDef,
    sheet_name: str,
    row: int,
    indent: bool = False,
) -> list[CellInstruction]:
    """Create cell instructions for a single field row.

    Args:
        field: The field definition.
        sheet_name: Target sheet name.
        row: Row number.
        indent: If True, indent the label (for compound sub-fields).

    Returns:
        List of CellInstruction (label, value cell, optional indicator).
    """
    instrs: list[CellInstruction] = []
    label_col = 2 if indent else 1
    label = f"  {field.label}" if indent else field.label

    # Label cell
    instrs.append(
        CellInstruction(
            sheet=sheet_name,
            row=row,
            col=label_col,
            value=label,
            bold=field.required,
        )
    )

    # Value cell (column B or C if indented, merged across)
    value_col = 3 if indent else 2
    merge = 3 if not indent else 2

    number_format = ""
    if field.type == "currency":
        number_format = "$#,##0.00"
    elif field.type == "date":
        number_format = "YYYY-MM-DD"

    dropdown = field.choices if field.type == "choice" else None
    if field.type == "boolean":
        dropdown = ["TRUE", "FALSE"]

    instrs.append(
        CellInstruction(
            sheet=sheet_name,
            row=row,
            col=value_col,
            value=field.default if field.default is not None else "",
            number_format=number_format,
            merge_cols=merge,
            dropdown_choices=dropdown,
            field_key=field.key,
        )
    )

    # Required indicator (column F)
    if field.required:
        instrs.append(
            CellInstruction(
                sheet=sheet_name,
                row=row,
                col=6,
                value="*",
                font_color=REQUIRED_INDICATOR_COLOR,
                bold=True,
            )
        )

    # Conditional note
    if field.conditional_on:
        cond = field.conditional_on
        instrs.append(
            CellInstruction(
                sheet=sheet_name,
                row=row,
                col=7,
                value="",
                note=f"Only required when {cond['field']} = {cond['value']}",
            )
        )

    return instrs


# ---------------------------------------------------------------------------
# Pure logic layer — plan_table_layout
# ---------------------------------------------------------------------------


def plan_table_layout(field: FieldDef, sheet_name: str) -> TablePlan:
    """Compute layout for a table-type field.

    Args:
        field: A table-type FieldDef.
        sheet_name: Target sheet name.

    Returns:
        TablePlan with headers and default rows.
    """
    columns = field.columns or []
    headers: list[CellInstruction] = []

    # Header row
    for col_idx, col in enumerate(columns, start=1):
        headers.append(
            CellInstruction(
                sheet=sheet_name,
                row=1,
                col=col_idx,
                value=col["label"],
                bold=True,
                bg_color=HEADER_COLOR,
                font_color=HEADER_FONT_COLOR,
                is_header=True,
            )
        )

    # Default rows
    default_rows: list[list[CellInstruction]] = []
    for row_idx, row_data in enumerate(field.default_rows or [], start=2):
        row_instrs: list[CellInstruction] = []
        for col_idx, col in enumerate(columns, start=1):
            col_type = col.get("type", "text")
            number_format = ""
            if col_type == "currency":
                number_format = "$#,##0.00"

            row_instrs.append(
                CellInstruction(
                    sheet=sheet_name,
                    row=row_idx,
                    col=col_idx,
                    value=row_data.get(col["key"], ""),
                    number_format=number_format,
                )
            )
        default_rows.append(row_instrs)

    return TablePlan(
        sheet=sheet_name,
        headers=headers,
        default_rows=default_rows,
    )
