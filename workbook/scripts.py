"""
docx_builder — xlwings Lite bootstrap script.

Paste this into the xlwings Lite add-in code editor.
The workbook fetches engine code, schemas, and templates from GitHub
at runtime. This script is the thin shell that wires everything up.
"""

from __future__ import annotations

from typing import Any

import yaml

# --- Configuration ---
GITHUB_BASE = "https://raw.githubusercontent.com/ccirone2/docx_builder/main"
_cache: dict[str, str] = {}
_engine: dict[str, dict] = {}

# Status messages
STATUS_CELL = "D3"
SCHEMA_DROPDOWN_CELL = "B3"
YAML_STAGING_CELL = "D20"


# --- Fetch helpers ---


def _fetch(path: str) -> str:
    """Fetch a file from GitHub with session caching.

    Args:
        path: Relative path within the repo.

    Returns:
        File contents as string.

    Raises:
        RuntimeError: If fetch fails.
    """
    url = f"{GITHUB_BASE}/{path}"
    if url not in _cache:
        import requests

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        _cache[url] = response.text
    return _cache[url]


def _load_module(name: str) -> dict:
    """Fetch and execute an engine module from GitHub.

    Args:
        name: Module name (e.g., "schema_loader").

    Returns:
        The module's namespace dict.
    """
    if name not in _engine:
        source = _fetch(f"engine/{name}.py")
        ns: dict[str, Any] = {"__name__": f"engine.{name}"}
        exec(source, ns)  # noqa: S102
        _engine[name] = ns
    return _engine[name]


def _set_status(book: Any, message: str) -> None:
    """Write a status message to the Control sheet.

    Args:
        book: xlwings Book object.
        message: Status text to display.
    """
    control = book.sheets["Control"]
    control[STATUS_CELL].value = message


def _get_github_base(book: Any) -> str:
    """Read the GitHub base URL from the Control sheet config area.

    Args:
        book: xlwings Book object.

    Returns:
        GitHub base URL string.
    """
    control = book.sheets["Control"]
    custom_url = control["D12"].value
    if custom_url and str(custom_url).strip().startswith("http"):
        return str(custom_url).strip().rstrip("/")
    return GITHUB_BASE


def _read_selected_schema(book: Any) -> str | None:
    """Read the currently selected schema name from the Control sheet.

    Args:
        book: xlwings Book object.

    Returns:
        Selected schema name, or None.
    """
    control = book.sheets["Control"]
    return control[SCHEMA_DROPDOWN_CELL].value


def _find_schema_entry(registry: dict, name: str) -> dict | None:
    """Find a registry entry by display name.

    Args:
        registry: Parsed registry dict.
        name: Schema display name.

    Returns:
        Registry entry dict, or None.
    """
    for entry in registry.get("schemas", []):
        if entry["name"] == name:
            return entry
    return None


def _read_data_from_sheets(book: Any, schema: Any) -> dict[str, Any]:
    """Read user-entered data from the data entry sheets.

    Args:
        book: xlwings Book object.
        schema: Parsed Schema object.

    Returns:
        Dict of {field_key: value}.
    """
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
    """Read a single field value from its sheet location.

    Args:
        book: xlwings Book object.
        field: FieldDef object.

    Returns:
        The field value, or None.
    """
    # Fields are laid out by the excel_builder, values are in column B/C
    for sheet in book.sheets:
        for row in range(2, 100):
            cell_value = sheet.range((row, 1)).value
            if cell_value and str(cell_value).strip() == field.label:
                return sheet.range((row, 2)).value
    return None


def _read_table_data(book: Any, field: Any) -> list[dict]:
    """Read table data from a dedicated table sheet.

    Args:
        book: xlwings Book object.
        field: Table FieldDef object.

    Returns:
        List of row dicts.
    """
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
    """Read compound field data from its group sheet.

    Args:
        book: xlwings Book object.
        field: Compound FieldDef object.

    Returns:
        Dict of sub-field values.
    """
    result = {}
    for sf in field.sub_fields or []:
        result[sf.key] = _read_field_value(book, sf)
    return result


# --- Scripts ---

try:
    from xlwings import script
except ImportError:
    # For testing outside xlwings Lite
    def script(button: str = "") -> Any:  # type: ignore[misc]
        """No-op decorator when xlwings is not available."""

        def decorator(func: Any) -> Any:
            return func

        return decorator


@script(button="[btn_init]Control!B5")
def initialize_sheets(book: Any) -> None:
    """Fetch registry, populate dropdown, build data entry sheets."""
    try:
        _set_status(book, "Loading...")
        _get_github_base(book)  # Reads custom URL if set

        # Fetch registry
        registry_text = _fetch("schemas/registry.yaml")
        registry = yaml.safe_load(registry_text)

        # Populate dropdown with schema names
        schema_names = [s["name"] for s in registry.get("schemas", [])]
        control = book.sheets["Control"]

        # Write schema names as a dropdown list
        if schema_names:
            control[SCHEMA_DROPDOWN_CELL].value = schema_names[0]

        # If a schema is selected, build its data entry sheets
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
def generate_document(book: Any) -> None:
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

        # Load schema
        schema_yaml = _fetch(f"schemas/{entry['schema_file']}")
        loader = _load_module("schema_loader")
        schema = loader["load_schema_from_text"](schema_yaml)

        # Read data from sheets
        data = _read_data_from_sheets(book, schema)

        # Validate
        result = loader["validate_data"](schema, data)
        if not result.valid:
            _set_status(book, f"Validation failed: {len(result.errors)} errors")
            return

        # Generate document
        doc_gen = _load_module("doc_generator")
        doc = doc_gen["generate_document"](schema, data)

        # Trigger download
        bridge = _load_module("file_bridge")
        filename = f"{entry['id']}.docx"
        bridge["trigger_docx_download"](doc, filename)

        _set_status(book, f"Document generated: {filename}")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_validate]Control!B9")
def validate_data(book: Any) -> None:
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
def export_data_yaml(book: Any) -> None:
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

        # Check if redaction is enabled
        control = book.sheets["Control"]
        redact = bool(control["D16"].value)

        exchange = _load_module("data_exchange")
        yaml_output = exchange["export_snapshot"](schema, data, redact=redact)

        # Write to staging cell
        control[YAML_STAGING_CELL].value = yaml_output
        _set_status(book, "Data exported to YAML (see staging cell)")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_import]Control!B13")
def import_data_yaml(book: Any) -> None:
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

        # Write imported data back to sheets
        # (simplified: write to staging cell for now)
        if warnings:
            _set_status(book, f"Imported with {len(warnings)} warnings")
        else:
            _set_status(book, f"Data imported successfully ({len(data)} fields)")

    except Exception as e:
        _set_status(book, f"Error: {e}")


@script(button="[btn_llm]Control!B15")
def generate_llm_prompt(book: Any) -> None:
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
def load_custom_schema(book: Any) -> None:
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
def load_custom_template(book: Any) -> None:
    """Read Python template source from staging cell."""
    try:
        _set_status(book, "Loading custom template...")

        control = book.sheets["Control"]
        source = control[YAML_STAGING_CELL].value

        if not source:
            _set_status(book, "Error: No template source in staging cell")
            return

        # Validate the template has a build_document function
        gh_loader = _load_module("github_loader")
        builder = gh_loader["load_template_builder"](str(source))

        if builder is None:
            _set_status(book, "Error: Template must define build_document()")
            return

        _set_status(book, "Custom template loaded successfully")

    except Exception as e:
        _set_status(book, f"Error: {e}")
