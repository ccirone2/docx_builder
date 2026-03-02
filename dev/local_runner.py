"""local_runner.py — Local orchestration of the engine pipeline.

Replicates runner.py's pipelines using direct engine imports instead of
network fetching + exec(). No pyodide dependency, no global state.

Functions:
  - init_workbook: Create Control + data entry sheets
  - read_data: Extract field values from workbook
  - fill_data: Write a data dict into workbook cells
  - validate: Run schema validation on data
  - generate: Produce a python-docx Document
  - export_yaml: Serialize data to YAML
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document

from engine.data_exchange import export_snapshot
from engine.doc_generator import generate_document
from engine.excel_control import plan_control_sheet
from engine.excel_plan import SheetPlan, _table_sheet_name, plan_sheets
from engine.excel_writer import build_sheets
from engine.schema_loader import Schema, ValidationResult, load_schema, validate_data

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
) -> dict[str, tuple[str, int, int]]:
    """Initialize a workbook with Control sheet and data entry sheets.

    Replicates runner.py init_workbook using direct engine imports.

    Args:
        book: A Book-like object (MockBook or xlwings Book).
        schema: The schema to build sheets for.
        schema_name: Display name to write into the Control B3 cell.

    Returns:
        field_locations dict mapping field_key → (sheet, row, col).
    """
    # 1. Build Control sheet
    control_instrs = plan_control_sheet()
    control_plan = SheetPlan(
        sheets=["Control"],
        instructions=control_instrs,
        field_locations={},
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

    return data_plan.field_locations


# ---------------------------------------------------------------------------
# Data reading
# ---------------------------------------------------------------------------


def read_data(
    book: Any,
    schema: Schema,
    field_locations: dict[str, tuple[str, int, int]],
) -> dict[str, Any]:
    """Read user-entered data from the workbook sheets.

    Uses field_locations for O(1) cell lookup (no scanning).

    Args:
        book: A Book-like object with populated sheets.
        schema: The schema defining fields.
        field_locations: Mapping of field_key → (sheet, row, col).

    Returns:
        Data dict with field_key → value.
    """
    data: dict[str, Any] = {}
    for group in schema.all_groups:
        for field in group.fields:
            if field.is_table:
                data[field.key] = _read_table_data(book, field)
            elif field.is_compound:
                data[field.key] = _read_compound_data(book, field, field_locations)
            else:
                data[field.key] = _read_field_value(book, field, field_locations)
    return data


def _read_field_value(
    book: Any,
    field: Any,
    field_locations: dict[str, tuple[str, int, int]],
) -> Any:
    """Read a single field value using the location index.

    Empty strings are normalized to None to match the data pipeline
    convention (init writes "" as default, but downstream code expects None).
    """
    loc = field_locations.get(field.key)
    if loc:
        sheet_name, row, col = loc
        if sheet_name in [s.name for s in book.sheets]:
            val = book.sheets[sheet_name].range((row, col)).value
            if isinstance(val, str) and val.strip() == "":
                return None
            return val
    return None


def _read_table_data(book: Any, field: Any) -> list[dict]:
    """Read table data from a dedicated table sheet."""
    sheet_name = _table_sheet_name(field.label)
    if sheet_name not in [s.name for s in book.sheets]:
        return []

    sheet = book.sheets[sheet_name]
    columns = field.columns or []
    rows = []

    for row_idx in range(2, 200):
        first_cell = sheet.range((row_idx, 1)).value
        if first_cell is None:
            break
        row_data = {}
        for col_idx, col in enumerate(columns, start=1):
            row_data[col["key"]] = sheet.range((row_idx, col_idx)).value
        rows.append(row_data)

    return rows


def _read_compound_data(
    book: Any,
    field: Any,
    field_locations: dict[str, tuple[str, int, int]],
) -> dict:
    """Read compound field data from its group sheet."""
    result = {}
    for sf in field.sub_fields or []:
        result[sf.key] = _read_field_value(book, sf, field_locations)
    return result


# ---------------------------------------------------------------------------
# Data writing
# ---------------------------------------------------------------------------


def fill_data(
    book: Any,
    schema: Schema,
    field_locations: dict[str, tuple[str, int, int]],
    data: dict[str, Any],
) -> None:
    """Write a data dict into the workbook cells.

    Args:
        book: A Book-like object with initialized sheets.
        schema: The schema defining fields.
        field_locations: Mapping of field_key → (sheet, row, col).
        data: Data dict with field_key → value.
    """
    for group in schema.all_groups:
        for field in group.fields:
            val = data.get(field.key)
            if val is None:
                continue

            if field.is_table:
                _write_table_data(book, field, val)
            elif field.is_compound:
                _write_compound_data(book, field, field_locations, val)
            else:
                _write_field_value(book, field, field_locations, val)


def _write_field_value(
    book: Any,
    field: Any,
    field_locations: dict[str, tuple[str, int, int]],
    value: Any,
) -> None:
    """Write a single field value using the location index."""
    loc = field_locations.get(field.key)
    if loc:
        sheet_name, row, col = loc
        if sheet_name in [s.name for s in book.sheets]:
            book.sheets[sheet_name].range((row, col)).value = value


def _write_table_data(book: Any, field: Any, rows: list[dict]) -> None:
    """Write table data to a dedicated table sheet."""
    sheet_name = _table_sheet_name(field.label)
    if sheet_name not in [s.name for s in book.sheets]:
        return

    sheet = book.sheets[sheet_name]
    columns = field.columns or []

    for row_idx, row_data in enumerate(rows, start=2):
        for col_idx, col in enumerate(columns, start=1):
            sheet.range((row_idx, col_idx)).value = row_data.get(col["key"])


def _write_compound_data(
    book: Any,
    field: Any,
    field_locations: dict[str, tuple[str, int, int]],
    values: dict,
) -> None:
    """Write compound field sub-values using the location index."""
    if not isinstance(values, dict):
        return
    for sf in field.sub_fields or []:
        sv = values.get(sf.key)
        if sv is not None:
            _write_field_value(book, sf, field_locations, sv)


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


def export_yaml(
    schema: Schema,
    data: dict[str, Any],
    redact: bool = False,
) -> str:
    """Export data as a YAML string.

    Args:
        schema: The schema definition.
        data: Data dict to export.
        redact: If True, mask fields marked redact=true.

    Returns:
        YAML string.
    """
    return export_snapshot(schema, data, redact=redact)
