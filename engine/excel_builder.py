"""
excel_builder.py — Build Excel data entry sheets from a schema definition.

Two-layer design:
  1. Pure logic layer (testable): computes sheet layouts, cell positions,
     dropdown lists, and formatting instructions as data structures.
  2. xlwings adapter layer (runtime only): writes those data structures
     to actual Excel sheets via the xlwings API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.config import (
    HEADER_COLOR,
    HEADER_FONT_COLOR,
    OPTIONAL_BG_COLOR,
    REQUIRED_INDICATOR_COLOR,
)
from engine.schema_loader import FieldDef, Schema

# --- Default GitHub base URL (used by plan_control_sheet) ---
_DEFAULT_GITHUB_BASE = (
    "https://raw.githubusercontent.com/ccirone2/docx_builder/main"
)

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


@dataclass
class SheetPlan:
    """Plan for which sheets to create and what cells to write."""

    sheets: list[str]
    instructions: list[CellInstruction]


@dataclass
class TablePlan:
    """Plan for a table-type field's sheet layout."""

    sheet: str
    headers: list[CellInstruction]
    default_rows: list[list[CellInstruction]]
    column_widths: list[int]


# ---------------------------------------------------------------------------
# Sheet name helpers
# ---------------------------------------------------------------------------


def _group_sheet_name(group_name: str, section: str) -> str:
    """Generate a sheet name for a field group."""
    prefix = "Data" if section == "core" else "Optional"
    return f"{prefix} - {group_name}"


def _table_sheet_name(field_label: str) -> str:
    """Generate a sheet name for a table field."""
    return f"Table - {field_label}"


# ---------------------------------------------------------------------------
# Pure logic layer — plan_sheets
# ---------------------------------------------------------------------------


def plan_sheets(schema: Schema) -> SheetPlan:
    """Determine which sheets to create and compute all cell instructions.

    Args:
        schema: The active schema definition.

    Returns:
        SheetPlan with sheet names and cell instructions.
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

    return SheetPlan(sheets=sheets, instructions=instructions)


# ---------------------------------------------------------------------------
# Pure logic layer — plan_control_sheet
# ---------------------------------------------------------------------------


def plan_control_sheet(github_base: str = "") -> list[CellInstruction]:
    """Compute cell instructions for the Control sheet layout.

    Creates the full Control sheet with title, document-type selector,
    status area, configuration section, and YAML staging area. This
    is the "easy button" — call once to scaffold the entire UI.

    Args:
        github_base: GitHub raw content URL for the config area.
            Defaults to the project's public repo URL.

    Returns:
        List of CellInstruction for the Control sheet.
    """
    sheet = "Control"
    url = github_base or _DEFAULT_GITHUB_BASE
    instrs: list[CellInstruction] = []

    # --- Title banner (Row 1, A1:F1) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=1,
            col=1,
            value="DOCUMENT GENERATOR",
            bold=True,
            bg_color=HEADER_COLOR,
            font_color=HEADER_FONT_COLOR,
            merge_cols=6,
            is_header=True,
        )
    )

    # --- Row 3: Document Type selector + status ---
    instrs.append(
        CellInstruction(
            sheet=sheet, row=3, col=1, value="Document Type:", bold=True,
        )
    )
    # B3: dropdown cell (populated later by initialize_sheets)
    instrs.append(
        CellInstruction(sheet=sheet, row=3, col=2, value="")
    )
    # D3: status cell
    instrs.append(
        CellInstruction(
            sheet=sheet, row=3, col=4, value="Ready — select a type and Initialize",
        )
    )

    # --- Button label rows (A column, next to xlwings button widgets) ---
    button_labels = [
        (5, "Initialize Sheets"),
        (7, "Generate Document"),
        (9, "Validate Data"),
        (11, "Export Data (YAML)"),
        (13, "Import Data (YAML)"),
        (15, "Generate LLM Prompt"),
        (17, "Load Custom Schema"),
        (19, "Load Custom Template"),
    ]
    for row, label in button_labels:
        instrs.append(
            CellInstruction(
                sheet=sheet, row=row, col=1, value=label, bold=True,
            )
        )

    # --- Configuration section (Row 10+) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=10,
            col=3,
            value="CONFIGURATION",
            bold=True,
            bg_color=OPTIONAL_BG_COLOR,
            merge_cols=2,
        )
    )
    instrs.append(
        CellInstruction(
            sheet=sheet, row=12, col=3, value="GitHub Repo URL:",
        )
    )
    instrs.append(
        CellInstruction(sheet=sheet, row=12, col=4, value=url)
    )

    # --- Redact toggle (Row 16) ---
    instrs.append(
        CellInstruction(
            sheet=sheet, row=16, col=3, value="Redact on Export:",
        )
    )
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=16,
            col=4,
            value="TRUE",
            dropdown_choices=["TRUE", "FALSE"],
        )
    )

    # --- YAML staging section (Row 18+) ---
    instrs.append(
        CellInstruction(
            sheet=sheet,
            row=18,
            col=3,
            value="YAML STAGING AREA",
            bold=True,
            bg_color=OPTIONAL_BG_COLOR,
            merge_cols=2,
        )
    )

    return instrs


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

    row_height = 60 if field.type == "multiline" else None
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
            row_height=row_height,
            dropdown_choices=dropdown,
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
        TablePlan with headers, default rows, and column widths.
    """
    columns = field.columns or []
    headers: list[CellInstruction] = []
    column_widths: list[int] = []

    # Header row
    for col_idx, col in enumerate(columns, start=1):
        number_format = ""
        if col.get("type") in ("currency",):
            number_format = "$#,##0.00"

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

        # Width hint based on type
        col_type = col.get("type", "text")
        if col_type in ("currency", "number"):
            column_widths.append(15)
        elif col_type == "boolean":
            column_widths.append(12)
        else:
            column_widths.append(25)

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
        column_widths=column_widths,
    )


# ---------------------------------------------------------------------------
# xlwings adapter layer (runtime only, not unit tested)
# ---------------------------------------------------------------------------


def build_sheets(book: Any, plan: SheetPlan) -> None:
    """Create sheets and write all cell instructions to an xlwings Book.

    Args:
        book: An xlwings Book object.
        plan: The SheetPlan to execute.
    """
    for sheet_name in plan.sheets:
        if sheet_name not in [s.name for s in book.sheets]:
            book.sheets.add(sheet_name)

    for instr in plan.instructions:
        sheet = book.sheets[instr.sheet]
        apply_cell(sheet, instr)


def apply_cell(sheet: Any, instr: CellInstruction) -> None:
    """Write a single cell to an xlwings Sheet with formatting.

    Args:
        sheet: An xlwings Sheet object.
        instr: The CellInstruction to apply.
    """
    cell = sheet.range((instr.row, instr.col))
    cell.value = instr.value

    if instr.merge_cols > 1:
        merge_range = sheet.range(
            (instr.row, instr.col),
            (instr.row, instr.col + instr.merge_cols - 1),
        )
        merge_range.merge()

    if instr.bold:
        cell.font.bold = True
    if instr.bg_color:
        cell.color = instr.bg_color
    if instr.font_color:
        cell.font.color = instr.font_color
    if instr.number_format:
        cell.number_format = instr.number_format
    if instr.row_height:
        cell.row_height = instr.row_height
    if instr.note:
        cell.note.text = instr.note
