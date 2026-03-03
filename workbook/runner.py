"""docx_builder runner — business logic fetched by the loader.

This file lives on GitHub and is fetched at runtime by loader.py.
Do NOT paste this file into xlwings Lite — use loader.py instead.

Changes here take effect the next time a user opens their workbook
(or clicks "Reload Scripts").
"""

import datetime
import sys
import types
from typing import Any

import yaml

# --- Configuration ---
GITHUB_REPO = "ccirone2/docx_builder"
GITHUB_BRANCH = "main"
GITHUB_BASE = (
    "https://raw.githubusercontent.com/"
    + GITHUB_REPO + "/" + GITHUB_BRANCH
)
_cache: dict[str, str] = {}
_engine: dict[str, dict] = {}

# Cell addresses on the Control sheet
SCHEMA_DROPDOWN_CELL = "B3"
YAML_STAGING_CELL = "D20"

# Module dependency graph (engine modules only)
_MODULE_DEPS: dict[str, list[str]] = {
    "log": [],
    "config": [],
    "schema_loader": ["log"],
    "scn": [],
    "excel_plan": ["config", "schema_loader"],
    "excel_control": ["config", "excel_plan"],
    "excel_writer": ["config", "excel_plan"],
    "data_exchange": ["log", "schema_loader"],
    "llm_helpers": ["schema_loader", "data_exchange"],
    "doc_generator": ["log", "schema_loader"],
    "validation_ux": ["schema_loader"],
    "file_bridge": ["log", "config"],
    "github_loader": ["log"],
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
    """Print a status message to the xlwings task pane output.

    Automatically prefixes with HH:MM:SS timestamp and a log level
    derived from the message content (ERROR / WARN / INFO).
    """
    stamp = datetime.datetime.now().strftime("%H:%M:%S")
    msg_lower = message.lower()
    if msg_lower.startswith("error") or "error" in msg_lower:
        level = "ERROR"
    elif "warn" in msg_lower or "failed" in msg_lower:
        level = "WARN "
    else:
        level = "INFO "
    print(f"[{stamp}] {level}  {message}")  # noqa: T201



def _read_selected_schema(book: Any) -> str | None:
    """Read the currently selected schema name from dropdown."""
    return book.sheets["Control"][SCHEMA_DROPDOWN_CELL].value


def _find_schema_entry(registry: dict, name: str) -> dict | None:
    """Find a registry entry by display name."""
    for entry in registry.get("schemas", []):
        if entry["name"] == name:
            return entry
    return None


def _prepare_schema(book: Any) -> tuple[Any, dict] | None:
    """Fetch registry, resolve selected schema, and load schema object.

    Common pipeline shared by most public functions. Fetches the registry
    from GitHub, reads the selected schema name from the Control sheet,
    looks up the registry entry, and loads the schema.

    Args:
        book: The xlwings Book object.

    Returns:
        Tuple of (schema, entry) on success, or None if no schema
        selected or schema not found (status message already set).
    """
    registry_text = _fetch("schemas/registry.yaml")
    registry = yaml.safe_load(registry_text)
    selected = _read_selected_schema(book)
    if not selected:
        _set_status(book, "Error: No document type selected")
        return None
    entry = _find_schema_entry(registry, selected)
    if not entry:
        _set_status(book, f"Error: Schema '{selected}' not found")
        return None
    schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
    loader = _load_module("schema_loader")
    schema = loader["load_schema_from_text"](schema_yaml)
    return schema, entry


def _read_column_a(book: Any, sheet_name: str) -> list[Any]:
    """Read all values from column A of a sheet."""
    if sheet_name not in [s.name for s in book.sheets]:
        return []
    sheet = book.sheets[sheet_name]
    cells: list[Any] = []
    for row in range(1, 1000):
        val = sheet.range((row, 1)).value
        cells.append(val)
        if len(cells) >= 10 and all(c is None for c in cells[-10:]):
            break
    while cells and cells[-1] is None:
        cells.pop()
    return cells


def _read_data_from_sheets(book: Any, schema: Any) -> dict[str, Any]:
    """Read user-entered data from the data entry sheets via SCN parser."""
    scn = _load_module("scn")
    config = _load_module("config")
    sheet_name = config.get("SHEET_DATA_ENTRY", "Data Entry")

    cells = _read_column_a(book, sheet_name)
    parsed = scn["parse_entry"](cells)

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
                        compound[sf.key] = parent_dict.get(sf.key)
                data[field.key] = compound
            else:
                data[field.key] = section_data.get(field.key)
    return data


def _read_table_data(book: Any, field: Any) -> list[dict]:
    """Read table data from a dedicated table sheet via SCN parser."""
    scn = _load_module("scn")
    planner = _load_module("excel_plan")
    sheet_name = planner["_table_sheet_name"](field.label)
    cells = _read_column_a(book, sheet_name)
    if not cells:
        return []
    parsed = scn["parse_entry"](cells)
    return parsed.get(field.key, [])


# --- Control sheet builder ---


def _fmt(cell, **kwargs):
    """Apply formatting to a cell, silently skipping unsupported operations.

    In xlwings Lite (Office.js), all operations are batched and executed
    when Python returns. An invalid operation rolls back the ENTIRE batch
    — including value writes. Only queue operations known to be safe.

    Supported: bold, color, font_color.
    NOT supported (will poison the batch): merge.
    """
    for key, val in kwargs.items():
        try:
            if key == "bold":
                cell.font.bold = val
            elif key == "color":
                cell.color = val
            elif key == "font_color":
                cell.font.color = val
            # merge intentionally omitted — breaks xlwings Lite batch
        except (NotImplementedError, AttributeError):
            pass



def _build_control_sheet(book: Any) -> None:
    """Create and populate the Control sheet layout.

    Uses direct xlwings calls — no network or module loading needed.
    Formatting is best-effort (some features not available in xlwings Lite).
    """
    sheet_names = [s.name for s in book.sheets]
    if "Control" not in sheet_names:
        book.sheets.add("Control")
    c = book.sheets["Control"]

    # Title banner (A1 — no merge, it poisons the xlwings Lite batch)
    c["A1"].value = "DOCUMENT GENERATOR"
    _fmt(c["A1"], bold=True, color=_HEADER_COLOR, font_color=_HEADER_FONT)

    # Document Type selector (Row 3)
    c["A3"].value = "Document Type:"
    _fmt(c["A3"], bold=True)

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
        _fmt(c.range((row, 1)), bold=True)

    # Configuration section
    c["C10"].value = "CONFIGURATION"
    _fmt(c["C10"], bold=True, color=_OPTIONAL_BG)
    c["C16"].value = "Redact on Export:"
    c["D16"].value = "TRUE"

    # Data staging area
    c["C18"].value = "DATA STAGING AREA"
    _fmt(c["C18"], bold=True, color=_OPTIONAL_BG)


# --- Public functions (called by loader.py) ---


def init_workbook(book: Any) -> None:
    """One-click workbook setup: create Control sheet, fetch schemas, build sheets."""
    _set_status(book, "init_workbook triggered")
    try:
        _build_control_sheet(book)
        _set_status(book, "Step 1/5: Fetching registry...")

        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)
        schema_names = [s["name"] for s in registry.get("schemas", [])]

        _set_status(book, f"Step 2/5: Found {len(schema_names)} schemas")
        control = book.sheets["Control"]
        selected = schema_names[0] if schema_names else None
        if selected:
            control[SCHEMA_DROPDOWN_CELL].value = selected

        # Build data entry sheets for the first available schema
        if selected:
            entry = _find_schema_entry(registry, selected)
            if entry:
                _set_status(book, f"Step 3/5: Fetching {entry['name']}...")
                schema_yaml = _fetch("schemas/" + entry["schema_file"])

                _set_status(book, "Step 4/5: Loading engine modules...")
                loader = _load_module("schema_loader")
                schema = loader["load_schema_from_text"](schema_yaml)

                _set_status(book, "Step 5/5: Building sheets...")
                planner = _load_module("excel_plan")
                plan = planner["plan_sheets"](schema)
                writer = _load_module("excel_writer")
                writer["build_sheets"](book, plan)

        # Remove default sheet left over from workbook creation
        for name in ("Sheet1", "Sheet 1"):
            if name in [s.name for s in book.sheets] and len(book.sheets) > 1:
                try:
                    book.sheets[name].delete()
                except Exception:
                    pass

        _set_status(book, f"Ready — {len(schema_names)} document types loaded")

    except Exception as e:
        _report_error(book, e)


def _report_error(book: Any, exc: Exception) -> None:
    """Print a detailed error, including traceback if no message."""
    msg = str(exc)
    if not msg:
        import traceback
        msg = traceback.format_exc()
    _set_status(book, f"Error [{type(exc).__name__}]: {msg}")


def _format_validation_line(message: str) -> str:
    """Convert a raw validation error/warning into a compact one-liner.

    Input formats from schema_loader:
        "Missing required field: Project Title (project_title)"
        "Missing required sub-field: Address → City (address.city)"
        "Field Label: Expected date format YYYY-MM-DD, got 'val'"

    Returns:
        Compact string like "Project Title: missing" or
        "Field Label: invalid date format".
    """
    # "Missing required field: Label (key)" or "Missing required sub-field: ..."
    if message.startswith("Missing required"):
        # Extract the label between the first ": " and the last " ("
        colon_idx = message.index(": ") + 2
        paren_idx = message.rfind(" (")
        label = message[colon_idx:paren_idx] if paren_idx > colon_idx else message[colon_idx:]
        return f"  - {label}: missing"

    # "Label: detail message" — keep label, shorten detail
    if ": " in message:
        label, detail = message.split(": ", 1)
        # Truncate long detail messages
        if len(detail) > 60:
            detail = detail[:57] + "..."
        return f"  - {label}: {detail}"

    return f"  - {message}"


def _report_validation(book: Any, validation: Any) -> None:
    """Print a compact summary + per-item detail for validation results.

    Args:
        book: The xlwings Book object (passed to _set_status).
        validation: A ValidationResult with .errors and .warnings lists.
    """
    if validation.errors:
        _set_status(book, f"Validation failed: {len(validation.errors)} errors")
        for err in validation.errors:
            _set_status(book, _format_validation_line(err))
    if validation.warnings:
        _set_status(book, f"Validation warnings: {len(validation.warnings)}")
        for warn in validation.warnings:
            _set_status(book, f"Warning: {_format_validation_line(warn)}")


def initialize_sheets(book: Any) -> None:
    """Fetch registry, populate dropdown, build data entry sheets."""
    _set_status(book, "initialize_sheets triggered")
    try:
        _set_status(book, "Loading...")

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

                planner = _load_module("excel_plan")
                plan = planner["plan_sheets"](schema)
                writer = _load_module("excel_writer")
                writer["build_sheets"](book, plan)

        _set_status(book, f"Ready — {len(schema_names)} document types loaded")

    except Exception as e:
        _report_error(book, e)


def generate_document(book: Any) -> None:
    """Read data, validate, build .docx, trigger download."""
    _set_status(book, "generate_document triggered")
    try:
        _set_status(book, "Generating document...")
        result = _prepare_schema(book)
        if result is None:
            return
        schema, entry = result
        data = _read_data_from_sheets(book, schema)
        loader = _load_module("schema_loader")
        validation = loader["validate_data"](schema, data)
        if not validation.valid:
            _report_validation(book, validation)
            return
        doc_gen = _load_module("doc_generator")
        doc = doc_gen["generate_document"](schema, data)
        bridge = _load_module("file_bridge")
        filename = f"{entry['id']}.docx"
        bridge["trigger_docx_download"](doc, filename)
        _set_status(book, f"Document generated: {filename}")
    except Exception as e:
        _report_error(book, e)


def validate_data(book: Any) -> None:
    """Run validation only, show results in status area."""
    _set_status(book, "validate_data triggered")
    try:
        _set_status(book, "Validating...")
        result = _prepare_schema(book)
        if result is None:
            return
        schema, entry = result
        data = _read_data_from_sheets(book, schema)
        loader = _load_module("schema_loader")
        validation = loader["validate_data"](schema, data)
        if validation.valid:
            msg = "Validation passed"
            if validation.warnings:
                msg += f" ({len(validation.warnings)} warnings)"
            _set_status(book, msg)
            if validation.warnings:
                _report_validation(book, validation)
        else:
            _report_validation(book, validation)
    except Exception as e:
        _report_error(book, e)


def export_data_yaml(book: Any) -> None:
    """Export data to YAML, write to staging cell."""
    _set_status(book, "export_data_yaml triggered")
    try:
        _set_status(book, "Exporting...")
        result = _prepare_schema(book)
        if result is None:
            return
        schema, entry = result
        data = _read_data_from_sheets(book, schema)
        control = book.sheets["Control"]
        redact = bool(control["D16"].value)
        exchange = _load_module("data_exchange")
        yaml_output = exchange["export_snapshot"](schema, data, redact=redact)
        control[YAML_STAGING_CELL].value = yaml_output
        _set_status(book, "Data exported to YAML (see staging cell)")
    except Exception as e:
        _report_error(book, e)


def import_data_yaml(book: Any) -> None:
    """Import YAML data from the staging cell."""
    _set_status(book, "import_data_yaml triggered")
    try:
        _set_status(book, "Importing...")
        control = book.sheets["Control"]
        yaml_text = control[YAML_STAGING_CELL].value
        if not yaml_text:
            _set_status(book, "Error: No YAML data in staging cell")
            return
        result = _prepare_schema(book)
        if result is None:
            return
        schema, entry = result
        exchange = _load_module("data_exchange")
        data, warnings = exchange["import_snapshot"](schema, str(yaml_text))
        if warnings:
            _set_status(book, f"Imported with {len(warnings)} warnings")
        else:
            _set_status(book, f"Data imported successfully ({len(data)} fields)")
    except Exception as e:
        _report_error(book, e)


def generate_llm_prompt(book: Any) -> None:
    """Generate LLM fill-in prompt, write to staging cell."""
    _set_status(book, "generate_llm_prompt triggered")
    try:
        _set_status(book, "Generating LLM prompt...")
        result = _prepare_schema(book)
        if result is None:
            return
        schema, entry = result
        data = _read_data_from_sheets(book, schema)
        llm = _load_module("llm_helpers")
        prompt = llm["generate_llm_prompt"](schema, existing_data=data, redact=True)
        control = book.sheets["Control"]
        control[YAML_STAGING_CELL].value = prompt
        _set_status(book, "LLM prompt generated (see staging cell)")
    except Exception as e:
        _report_error(book, e)


def load_custom_schema(book: Any) -> None:
    """Read YAML from staging cell and register as local schema."""
    _set_status(book, "load_custom_schema triggered")
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
        _report_error(book, e)


def load_custom_template(book: Any) -> None:
    """Read Python template source from staging cell."""
    _set_status(book, "load_custom_template triggered")
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
        _report_error(book, e)
