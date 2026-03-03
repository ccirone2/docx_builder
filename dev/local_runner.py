"""local_runner.py — Local orchestration of the engine pipeline.

Replicates runner.py's pipelines using direct engine imports instead of
network fetching + exec(). No pyodide dependency, no global state.

Functions:
  - init_workbook: Create Control + data entry sheets
  - read_data: Extract field values from workbook via SCN parser
  - fill_data: Write a data dict into workbook via SCN layout
  - validate: Run schema validation on data
  - generate: Produce a python-docx Document
  - export_scn: Serialize data to SCN
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

from engine.config import SHEET_DATA_ENTRY
from engine.data_exchange import export_snapshot
from engine.doc_generator import generate_document
from engine.excel_control import plan_control_sheet
from engine.excel_plan import SheetPlan, _table_sheet_name, plan_sheets
from engine.excel_writer import build_sheets
from engine.schema_loader import Schema, ValidationResult, load_schema, validate_data
from engine.scn import _get_nested, parse_entry

# ---------------------------------------------------------------------------
# Schema loading helpers
# ---------------------------------------------------------------------------

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_default_schema(schema_id: str = "rfq_electric_utility") -> Schema:
    """Load a schema by ID from the local schemas/ directory.

    Args:
        schema_id: Schema filename stem (without .yaml extension).

    Returns:
        Parsed Schema object.

    Raises:
        FileNotFoundError: If schema file doesn't exist.
    """
    path = _SCHEMA_DIR / f"{schema_id}.yaml"
    return load_schema(path)


# ---------------------------------------------------------------------------
# Workbook initialization
# ---------------------------------------------------------------------------


def _remove_default_sheet(book: Any) -> None:
    """Remove the default 'Sheet1' that Excel creates for new workbooks."""
    for name in ("Sheet1", "Sheet 1"):
        if name in [s.name for s in book.sheets]:
            # Only delete if there are other sheets (can't delete the last sheet)
            if len(book.sheets) > 1:
                book.sheets[name].delete()


def init_workbook(
    book: Any,
    schema: Schema,
    schema_name: str = "",
) -> None:
    """Initialize a workbook with Control sheet and data entry sheets.

    Replicates runner.py init_workbook using direct engine imports.

    Args:
        book: A Book-like object (MockBook or xlwings Book).
        schema: The schema to build sheets for.
        schema_name: Display name to write into the Control B3 cell.
    """
    # 1. Build Control sheet
    control_instrs = plan_control_sheet()
    control_plan = SheetPlan(
        sheets=["Control"],
        instructions=control_instrs,
    )
    build_sheets(book, control_plan)

    # 2. Write schema name to dropdown cell
    if schema_name:
        book.sheets["Control"]["B3"].value = schema_name

    # 3. Build data entry sheets
    data_plan = plan_sheets(schema)
    build_sheets(book, data_plan)

    # 4. Remove default "Sheet1" left over from workbook creation
    _remove_default_sheet(book)


# ---------------------------------------------------------------------------
# Data reading — SCN parser
# ---------------------------------------------------------------------------


def _read_column_a(book: Any, sheet_name: str) -> list[Any]:
    """Read all values from column A of a sheet."""
    if sheet_name not in [s.name for s in book.sheets]:
        return []
    sheet = book.sheets[sheet_name]
    cells: list[Any] = []
    for row in range(1, 1000):
        val = sheet.range((row, 1)).value
        cells.append(val)
        # Stop after 10 consecutive empty cells
        if len(cells) >= 10 and all(c is None for c in cells[-10:]):
            break
    # Trim trailing Nones
    while cells and cells[-1] is None:
        cells.pop()
    return cells


def read_data(
    book: Any,
    schema: Schema,
) -> dict[str, Any]:
    """Read user-entered data from the workbook using SCN parser.

    Reads the Data Entry sheet column A via parse_entry(), then reads
    table sheets separately.

    Args:
        book: A Book-like object with populated sheets.
        schema: The schema defining fields.

    Returns:
        Data dict with field_key → value.
    """
    # Parse Data Entry sheet
    cells = _read_column_a(book, SHEET_DATA_ENTRY)
    parsed = parse_entry(cells)

    # Flatten sectioned data into flat dict
    data: dict[str, Any] = {}
    for group in schema.all_groups:
        section_data = parsed.get(group.name, {})

        for field in group.fields:
            if field.is_table:
                data[field.key] = _read_table_data(book, field)
            elif field.is_compound:
                compound: dict[str, Any] = {}
                parent_dict = section_data.get(field.key, {})
                if isinstance(parent_dict, dict):
                    for sf in field.sub_fields or []:
                        val = parent_dict.get(sf.key)
                        compound[sf.key] = val
                data[field.key] = compound
            else:
                data[field.key] = section_data.get(field.key)

    return data


def _read_table_data(book: Any, field: Any) -> list[dict]:
    """Read table data from a dedicated table sheet via SCN parser."""
    sheet_name = _table_sheet_name(field.label)
    cells = _read_column_a(book, sheet_name)
    if not cells:
        return []

    parsed = parse_entry(cells)
    return parsed.get(field.key, [])


# ---------------------------------------------------------------------------
# Data writing — SCN layout
# ---------------------------------------------------------------------------


def fill_data(
    book: Any,
    schema: Schema,
    data: dict[str, Any],
) -> None:
    """Write a data dict into the workbook cells.

    Walks column A of the Data Entry sheet, finds key: rows, and writes
    the corresponding value into the next row. Table fields are written
    to their separate sheets.

    Args:
        book: A Book-like object with initialized sheets.
        schema: The schema defining fields.
        data: Data dict with field_key → value.
    """
    # Write simple/compound fields to Data Entry sheet
    if SHEET_DATA_ENTRY not in [s.name for s in book.sheets]:
        return
    sheet = book.sheets[SHEET_DATA_ENTRY]

    for row in range(1, 1000):
        cell_val = sheet.range((row, 1)).value
        if cell_val is None:
            continue
        line = str(cell_val).strip()
        if line.endswith(":") and not line.startswith(";;"):
            key = line[:-1].strip()
            val = _get_nested(data, key)
            if isinstance(val, list):
                # Write list items in consecutive rows after key:
                for i, item in enumerate(val):
                    sheet.range((row + 1 + i, 1)).value = f"- {item}"
            elif val is not None:
                sheet.range((row + 1, 1)).value = val

    # Write table fields to their separate sheets
    for group in schema.all_groups:
        for field in group.fields:
            if field.is_table:
                table_val = data.get(field.key)
                if isinstance(table_val, list):
                    _write_table_data(book, field, table_val)


def _write_table_data(book: Any, field: Any, rows: list[dict]) -> None:
    """Write table data to a dedicated table sheet using SCN format."""
    sheet_name = _table_sheet_name(field.label)
    if sheet_name not in [s.name for s in book.sheets]:
        return

    sheet = book.sheets[sheet_name]
    columns = field.columns or []

    # Start after the header comment row
    row = 2
    for row_data in rows:
        sheet.range((row, 1)).value = f"+{field.key}"
        row += 1
        for col_def in columns:
            sheet.range((row, 1)).value = f"{col_def['key']}:"
            row += 1
            sheet.range((row, 1)).value = row_data.get(col_def["key"])
            row += 1


# ---------------------------------------------------------------------------
# Thin wrappers
# ---------------------------------------------------------------------------


def validate(schema: Schema, data: dict[str, Any]) -> ValidationResult:
    """Validate data against a schema.

    Args:
        schema: The schema definition.
        data: Data dict to validate.

    Returns:
        ValidationResult with valid flag, errors, and warnings.
    """
    return validate_data(schema, data)


def generate(
    schema: Schema,
    data: dict[str, Any],
    output_path: str | Path | None = None,
) -> Document:
    """Generate a .docx Document from schema and data.

    Args:
        schema: The schema definition.
        data: Validated data dict.
        output_path: If provided, save the document to this path.

    Returns:
        The generated python-docx Document object.
    """
    doc = generate_document(schema, data)
    if output_path:
        doc.save(str(output_path))
    return doc


def export_scn(
    schema: Schema,
    data: dict[str, Any],
    redact: bool = False,
) -> str:
    """Export data as an SCN string.

    Args:
        schema: The schema definition.
        data: Data dict to export.
        redact: If True, mask fields marked redact=true.

    Returns:
        SCN string.
    """
    return export_snapshot(schema, data, redact=redact)
