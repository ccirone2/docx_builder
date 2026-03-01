"""
docx_builder — xlwings Lite bootstrap script.

Paste this into the xlwings Lite add-in code editor.
The workbook fetches engine code, schemas, and templates from GitHub
at runtime. This script is the thin shell that wires everything up.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import yaml

try:
    import xlwings as xw
except ImportError:
    xw = None  # type: ignore[assignment]

# --- Configuration ---
GITHUB_BASE = (
    "https://raw.githubusercontent.com"
    "/ccirone2/docx_builder/main"
)
_cache: dict[str, str] = {}
_engine: dict[str, dict] = {}

# Cell addresses on the Control sheet
STATUS_CELL = "D3"
SCHEMA_DROPDOWN_CELL = "B3"
YAML_STAGING_CELL = "D20"

# Module dependency graph (engine modules only)
_MODULE_DEPS: dict[str, list[str]] = {
    "config": [],
    "schema_loader": [],
    "excel_builder": ["config", "schema_loader"],
    "data_exchange": ["schema_loader"],
    "doc_generator": ["schema_loader"],
    "validation_ux": ["schema_loader"],
    "file_bridge": [],
    "github_loader": [],
}

# Formatting constants (duplicated from engine/config.py so
# init_workbook can build the Control sheet without a network call)
_HEADER_COLOR = "#1F4E79"
_HEADER_FONT = "#FFFFFF"
_OPTIONAL_BG = "#F2F2F2"


# --- Fetch helpers ---


def _fetch(path: str) -> str:
    """Fetch a file from GitHub with session caching.

    Uses pyodide.http.open_url in Pyodide, falls back to
    urllib for standard Python.

    Args:
        path: Relative path within the repo.

    Returns:
        File contents as string.
    """
    url = f"{GITHUB_BASE}/{path}"
    if url not in _cache:
        try:
            # Pyodide environment (xlwings Lite)
            from pyodide.http import open_url  # type: ignore[import-untyped]

            _cache[url] = open_url(url).read()
        except ImportError:
            # Standard Python (development / testing)
            from urllib.request import urlopen

            with urlopen(url, timeout=15) as resp:  # noqa: S310
                _cache[url] = resp.read().decode()
    return _cache[url]


def _load_module(name: str) -> dict:
    """Fetch and execute an engine module from GitHub.

    Loads dependencies first and registers every module in
    sys.modules so that cross-module imports work.

    Args:
        name: Module name (e.g., "schema_loader").

    Returns:
        The module's namespace dict.
    """
    if name not in _engine:
        # Ensure the 'engine' package exists in sys.modules
        if "engine" not in sys.modules:
            pkg = types.ModuleType("engine")
            pkg.__path__ = []  # type: ignore[attr-defined]
            sys.modules["engine"] = pkg

        # Load dependencies first
        for dep in _MODULE_DEPS.get(name, []):
            if dep not in _engine:
                _load_module(dep)

        source = _fetch(f"engine/{name}.py")
        mod = types.ModuleType(f"engine.{name}")
        sys.modules[f"engine.{name}"] = mod
        exec(source, mod.__dict__)  # noqa: S102
        _engine[name] = mod.__dict__
    return _engine[name]


def _set_status(book: Any, message: str) -> None:
    """Write a status message to the Control sheet."""
    book.sheets["Control"][STATUS_CELL].value = message


def _get_github_base(book: Any) -> str:
    """Read custom GitHub URL from Control sheet, or return default."""
    global GITHUB_BASE  # noqa: PLW0603
    custom_url = book.sheets["Control"]["D12"].value
    if custom_url and str(custom_url).strip().startswith("http"):
        GITHUB_BASE = str(custom_url).strip().rstrip("/")
    return GITHUB_BASE


def _read_selected_schema(book: Any) -> str | None:
    """Read the currently selected schema name from dropdown."""
    return book.sheets["Control"][SCHEMA_DROPDOWN_CELL].value


def _find_schema_entry(registry: dict, name: str) -> dict | None:
    """Find a registry entry by display name."""
    for entry in registry.get("schemas", []):
        if entry["name"] == name:
            return entry
    return None


def _read_data_from_sheets(book: Any, schema: Any) -> dict[str, Any]:
    """Read user-entered data from the data entry sheets."""
    data: dict[str, Any] = {}
    for group in schema.all_groups:
        for field in group.fields:
            if field.is_table:
                data[field.key] = _read_table_data(book, field)
            elif field.is_compound:
                data[field.key] = _read_compound_data(book, field)
            else:
                data[field.key] = _read_field_value(book, field)
    return data


def _read_field_value(book: Any, field: Any) -> Any:
    """Read a single field value from its sheet location."""
    for sheet in book.sheets:
        for row in range(2, 100):
            cell_value = sheet.range((row, 1)).value
            if cell_value and str(cell_value).strip() == field.label:
                return sheet.range((row, 2)).value
    return None


def _read_table_data(book: Any, field: Any) -> list[dict]:
    """Read table data from a dedicated table sheet."""
    sheet_name = f"Table - {field.label}"
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


def _read_compound_data(book: Any, field: Any) -> dict:
    """Read compound field data from its group sheet."""
    result = {}
    for sf in field.sub_fields or []:
        result[sf.key] = _read_field_value(book, sf)
    return result


# --- Scripts ---

if xw is not None:
    script = xw.script
else:
    # For testing outside xlwings Lite
    def script(button: str = "") -> Any:  # type: ignore[misc]
        """No-op decorator when xlwings is not available."""

        def decorator(func: Any) -> Any:
            return func

        return decorator


def _build_control_sheet(book: xw.Book) -> None:
    """Create and populate the Control sheet layout.

    Uses direct xlwings calls — no network or module loading needed.
    """
    sheet_names = [s.name for s in book.sheets]
    if "Control" not in sheet_names:
        book.sheets.add("Control")
    c = book.sheets["Control"]

    # Title banner (A1:F1)
    c["A1"].value = "DOCUMENT GENERATOR"
    c.range("A1:F1").merge()
    c["A1"].font.bold = True
    c["A1"].color = _HEADER_COLOR
    c["A1"].font.color = _HEADER_FONT

    # Document Type selector (Row 3)
    c["A3"].value = "Document Type:"
    c["A3"].font.bold = True
    c[STATUS_CELL].value = "Ready"

    # Button labels (column A, next to xlwings button widgets)
    for row, label in [
        (5, "Initialize Sheets"),
        (7, "Generate Document"),
        (9, "Validate Data"),
        (11, "Export Data (YAML)"),
        (13, "Import Data (YAML)"),
        (15, "Generate LLM Prompt"),
        (17, "Load Custom Schema"),
        (19, "Load Custom Template"),
    ]:
        c.range((row, 1)).value = label
        c.range((row, 1)).font.bold = True

    # Configuration section
    c["C10"].value = "CONFIGURATION"
    c["C10"].font.bold = True
    c["C10"].color = _OPTIONAL_BG
    c["C12"].value = "GitHub Repo URL:"
    c["D12"].value = GITHUB_BASE
    c["C16"].value = "Redact on Export:"
    c["D16"].value = "TRUE"

    # YAML staging area
    c["C18"].value = "YAML STAGING AREA"
    c["C18"].font.bold = True
    c["C18"].color = _OPTIONAL_BG


@script(button="[btn_easy_init]Control!D5")
def init_workbook(book: xw.Book) -> None:
    """One-click workbook setup: create Control sheet, fetch schemas, build sheets.

    This is the "easy button". Paste the script, click this, done.
    """
    try:
        _build_control_sheet(book)
        _set_status(book, "Fetching schemas...")

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        schema_names = [s["name"] for s in registry.get("schemas", [])]

        control = book.sheets["Control"]
        if schema_names:
            control[SCHEMA_DROPDOWN_CELL].value = schema_names[0]

        # Build data entry sheets for the first available schema
        selected = _read_selected_schema(book)
        if selected:
            entry = _find_schema_entry(registry, selected)
            if entry:
                _set_status(book, f"Building sheets for {entry['name']}...")
                schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
                loader = _load_module("schema_loader")
                schema = loader["load_schema_from_text"](schema_yaml)

                builder = _load_module("excel_builder")
                plan = builder["plan_sheets"](schema)
                builder["build_sheets"](book, plan)

        _set_status(book, f"Ready — {len(schema_names)} document types loaded")

    except Exception as e:
        try:
            _set_status(book, f"Error: {e}")
        except Exception:
            pass


@script(button="[btn_init]Control!B5")
def initialize_sheets(book: xw.Book) -> None:
    """Fetch registry, populate dropdown, build data entry sheets."""
    try:
        _set_status(book, "Loading...")
        _get_github_base(book)

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)

        schema_names = [s["name"] for s in registry.get("schemas", [])]
        control = book.sheets["Control"]

        if schema_names:
            control[SCHEMA_DROPDOWN_CELL].value = schema_names[0]

        selected = _read_selected_schema(book)
        if selected:
            entry = _find_schema_entry(registry, selected)
            if entry:
                schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
                loader = _load_module("schema_loader")
                schema = loader["load_schema_from_text"](schema_yaml)

                builder = _load_module("excel_builder")
                plan = builder["plan_sheets"](schema)
                builder["build_sheets"](book, plan)

        _set_status(book, f"Ready — {len(schema_names)} document types loaded")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_generate]Control!B7")
def generate_document(book: xw.Book) -> None:
    """Read data, validate, build .docx, trigger download."""
    try:
        _set_status(book, "Generating document...")

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        selected = _read_selected_schema(book)

        if not selected:
            _set_status(book, "Error: No document type selected")
            return

        entry = _find_schema_entry(registry, selected)
        if not entry:
            _set_status(book, f"Error: Schema '{selected}' not found")
            return

        schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
        loader = _load_module("schema_loader")
        schema = loader["load_schema_from_text"](schema_yaml)

        data = _read_data_from_sheets(book, schema)

        result = loader["validate_data"](schema, data)
        if not result.valid:
            _set_status(book, f"Validation failed: {len(result.errors)} errors")
            return

        doc_gen = _load_module("doc_generator")
        doc = doc_gen["generate_document"](schema, data)

        bridge = _load_module("file_bridge")
        filename = f"{entry['id']}.docx"
        bridge["trigger_docx_download"](doc, filename)

        _set_status(book, f"Document generated: {filename}")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_validate]Control!B9")
def validate_data(book: xw.Book) -> None:
    """Run validation only, show results in status area."""
    try:
        _set_status(book, "Validating...")

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        selected = _read_selected_schema(book)

        if not selected:
            _set_status(book, "Error: No document type selected")
            return

        entry = _find_schema_entry(registry, selected)
        if not entry:
            _set_status(book, f"Error: Schema '{selected}' not found")
            return

        schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
        loader = _load_module("schema_loader")
        schema = loader["load_schema_from_text"](schema_yaml)

        data = _read_data_from_sheets(book, schema)
        result = loader["validate_data"](schema, data)

        if result.valid:
            msg = "Validation passed"
            if result.warnings:
                msg += f" ({len(result.warnings)} warnings)"
            _set_status(book, msg)
        else:
            _set_status(book, f"Validation failed: {len(result.errors)} errors")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_export]Control!B11")
def export_data_yaml(book: xw.Book) -> None:
    """Export data to YAML, write to staging cell."""
    try:
        _set_status(book, "Exporting...")

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        selected = _read_selected_schema(book)

        if not selected:
            _set_status(book, "Error: No document type selected")
            return

        entry = _find_schema_entry(registry, selected)
        if not entry:
            _set_status(book, f"Error: Schema '{selected}' not found")
            return

        schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
        loader = _load_module("schema_loader")
        schema = loader["load_schema_from_text"](schema_yaml)

        data = _read_data_from_sheets(book, schema)

        control = book.sheets["Control"]
        redact = bool(control["D16"].value)

        exchange = _load_module("data_exchange")
        yaml_output = exchange["export_snapshot"](schema, data, redact=redact)

        control[YAML_STAGING_CELL].value = yaml_output
        _set_status(book, "Data exported to YAML (see staging cell)")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_import]Control!B13")
def import_data_yaml(book: xw.Book) -> None:
    """Import YAML data from the staging cell."""
    try:
        _set_status(book, "Importing...")

        control = book.sheets["Control"]
        yaml_text = control[YAML_STAGING_CELL].value

        if not yaml_text:
            _set_status(book, "Error: No YAML data in staging cell")
            return

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        selected = _read_selected_schema(book)

        if not selected:
            _set_status(book, "Error: No document type selected")
            return

        entry = _find_schema_entry(registry, selected)
        if not entry:
            _set_status(book, f"Error: Schema '{selected}' not found")
            return

        schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
        loader = _load_module("schema_loader")
        schema = loader["load_schema_from_text"](schema_yaml)

        exchange = _load_module("data_exchange")
        data, warnings = exchange["import_snapshot"](schema, str(yaml_text))

        if warnings:
            _set_status(book, f"Imported with {len(warnings)} warnings")
        else:
            _set_status(book, f"Data imported successfully ({len(data)} fields)")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_llm]Control!B15")
def generate_llm_prompt(book: xw.Book) -> None:
    """Generate LLM fill-in prompt, write to staging cell."""
    try:
        _set_status(book, "Generating LLM prompt...")

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        selected = _read_selected_schema(book)

        if not selected:
            _set_status(book, "Error: No document type selected")
            return

        entry = _find_schema_entry(registry, selected)
        if not entry:
            _set_status(book, f"Error: Schema '{selected}' not found")
            return

        schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
        loader = _load_module("schema_loader")
        schema = loader["load_schema_from_text"](schema_yaml)

        data = _read_data_from_sheets(book, schema)

        exchange = _load_module("data_exchange")
        prompt = exchange["generate_llm_prompt"](
            schema,
            existing_data=data,
            redact=True,
        )

        control = book.sheets["Control"]
        control[YAML_STAGING_CELL].value = prompt
        _set_status(book, "LLM prompt generated (see staging cell)")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_load_schema]Control!B17")
def load_custom_schema(book: xw.Book) -> None:
    """Read YAML from staging cell and register as local schema."""
    try:
        _set_status(book, "Loading custom schema...")

        control = book.sheets["Control"]
        yaml_text = control[YAML_STAGING_CELL].value

        if not yaml_text:
            _set_status(book, "Error: No YAML in staging cell")
            return

        gh_loader = _load_module("github_loader")
        entry = gh_loader["register_local_schema"](str(yaml_text))

        if entry is None:
            _set_status(book, "Error: Invalid schema YAML")
            return

        _set_status(book, f"Custom schema loaded: {entry.name}")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_load_template]Control!B19")
def load_custom_template(book: xw.Book) -> None:
    """Read Python template source from staging cell."""
    try:
        _set_status(book, "Loading custom template...")

        control = book.sheets["Control"]
        source = control[YAML_STAGING_CELL].value

        if not source:
            _set_status(book, "Error: No template source in staging cell")
            return

        gh_loader = _load_module("github_loader")
        builder = gh_loader["load_template_builder"](str(source))

        if builder is None:
            _set_status(book, "Error: Template must define build_document()")
            return

        _set_status(book, "Custom template loaded successfully")

    except Exception as e:
        _set_status(book, f"Error: {e}")
