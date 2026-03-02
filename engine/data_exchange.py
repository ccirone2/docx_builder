"""
data_exchange.py — Import/export user data as YAML for reuse and LLM assistance.

Three main workflows:
  1. EXPORT: Read data from Excel → serialize to YAML → copy to clipboard
  2. IMPORT: Paste YAML from clipboard → parse → validate → write to Excel
  3. LLM PROMPT: Generate a schema-aware YAML prompt that an LLM can fill in

The YAML format is designed to be:
  - Human-readable (for manual editing or reuse across documents)
  - LLM-friendly (structured enough that an LLM can fill it in reliably)
  - Round-trippable (export → edit → import without data loss)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import yaml

from engine.schema_loader import FieldDef, FieldGroup, Schema

# ---------------------------------------------------------------------------
# YAML formatting helpers
# ---------------------------------------------------------------------------


class _YAMLDumper(yaml.SafeDumper):
    """Custom YAML dumper that produces clean, human-readable output."""

    pass


def _str_representer(dumper, data):
    """Use literal block style for multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def _none_representer(dumper, data):
    """Represent None as empty string for cleaner YAML."""
    return dumper.represent_scalar("tag:yaml.org,2002:null", "")


_YAMLDumper.add_representer(str, _str_representer)
_YAMLDumper.add_representer(type(None), _none_representer)


def _to_yaml(data: dict) -> str:
    """Serialize a dict to clean YAML."""
    return yaml.dump(
        data,
        Dumper=_YAMLDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

# Placeholder text that replaces redacted values. The LLM sees this and knows
# the field exists but the real data was withheld.
REDACTED_TEXT = "[REDACTED]"
REDACTED_NUMBER = 0
REDACTED_TABLE_TEXT = "[REDACTED]"


def _redact_value(field: FieldDef, value: Any) -> Any:
    """Replace a field value with a redaction placeholder."""
    if value is None:
        return None
    if field.type in ("number", "currency"):
        return REDACTED_NUMBER
    if field.type == "boolean":
        return value  # booleans are structural, not sensitive
    return REDACTED_TEXT


def _redact_table_row(field: FieldDef, row: dict) -> dict:
    """Redact specific columns within a table row."""
    if not field.columns:
        return row
    redacted_row = {}
    for col in field.columns:
        key = col["key"]
        if col.get("redact", False) and key in row:
            if col.get("type") in ("number", "currency"):
                redacted_row[key] = REDACTED_NUMBER
            else:
                redacted_row[key] = REDACTED_TABLE_TEXT
        else:
            redacted_row[key] = row.get(key)
    return redacted_row


def _redact_compound(field: FieldDef, value: dict) -> dict:
    """Redact specific sub-fields within a compound field."""
    if not field.sub_fields or not isinstance(value, dict):
        return value
    result = {}
    for sf in field.sub_fields:
        sv = value.get(sf.key)
        if sf.redact and sv is not None:
            result[sf.key] = _redact_value(sf, sv)
        else:
            result[sf.key] = sv
    return result


# ---------------------------------------------------------------------------
# EXPORT — Excel data → YAML string
# ---------------------------------------------------------------------------


def _export_field_value(field: FieldDef, val: Any, redact: bool) -> Any:
    """Export a single field value with optional redaction. Handles all types."""
    if redact and field.redact:
        return _redact_value(field, val)
    if redact and field.is_table and field.has_redactable_columns:
        if isinstance(val, list):
            return [_redact_table_row(field, row) for row in val]
    if redact and field.is_compound and field.has_redactable_sub_fields:
        if isinstance(val, dict):
            return _redact_compound(field, val)
    return _serialize_value(field, val)


def export_snapshot(
    schema: Schema,
    data: dict[str, Any],
    redact: bool = False,
) -> str:
    """
    Export all user data as a YAML snapshot.

    Args:
        schema: The active schema definition.
        data: Flat dict of {field_key: value} from Excel.
              Compound fields are stored as {parent_key: {sub_key: value}}.
        redact: If True, fields marked with redact=true in the schema
                are replaced with placeholder values. Use this when
                sharing data with an LLM or externally.

    Returns:
        YAML string ready for clipboard.
    """
    output = {
        "_meta": {
            "schema_id": schema.id,
            "schema_version": schema.version,
            "export_type": "full_snapshot",
            "redacted": redact,
        },
    }

    # Core fields, organized by group
    for group in schema.core_groups:
        group_data = {}
        for field in group.fields:
            val = data.get(field.key)
            group_data[field.key] = _export_field_value(field, val, redact)
        output[_group_key(group)] = group_data

    # Optional fields
    for group in schema.optional_groups:
        group_data = {}
        for field in group.fields:
            val = data.get(field.key)
            if val is not None:
                group_data[field.key] = _export_field_value(field, val, redact)
        if group_data:
            output[_group_key(group)] = group_data

    # Flexible fields — always redacted entirely when redact=True,
    # since we can't know what's sensitive in user-defined fields
    flex_data = data.get("_flexible_fields")
    if flex_data:
        if redact:
            output["additional_information"] = (
                [
                    {"field_label": entry.get("field_label", ""), "field_value": REDACTED_TEXT}
                    for entry in flex_data
                ]
                if isinstance(flex_data, list)
                else REDACTED_TEXT
            )
        else:
            output["additional_information"] = flex_data

    return _to_yaml(output)


def _group_key(group: FieldGroup) -> str:
    """Convert group name to a YAML-friendly key."""
    return group.name.lower().replace(" ", "_").replace("&", "and")


def _serialize_value(field: FieldDef, value: Any) -> Any:
    """Convert a field value to a YAML-safe type."""
    if value is None:
        return None
    if field.type == "date" and isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    if field.type == "boolean":
        return bool(value)
    if field.type == "table" and isinstance(value, list):
        return value  # list of dicts, YAML handles natively
    if field.type == "compound" and isinstance(value, dict):
        return value  # dict of sub-field values
    return value


# ---------------------------------------------------------------------------
# IMPORT — YAML string → validated data dict
# ---------------------------------------------------------------------------


def import_snapshot(schema: Schema, yaml_text: str) -> tuple[dict[str, Any], list[str]]:
    """
    Parse a YAML snapshot and extract field values.

    Args:
        schema: The active schema definition.
        yaml_text: YAML string (from clipboard).

    Returns:
        Tuple of (data_dict, warnings).
        data_dict: {field_key: value} ready to write to Excel.
        warnings: List of non-fatal issues found during import.
    """
    warnings = []

    try:
        raw = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return {}, [f"YAML parse error: {e}"]

    if not isinstance(raw, dict):
        return {}, ["Expected a YAML mapping (dict) at the top level."]

    # Check schema compatibility
    meta = raw.get("_meta", {})
    if meta.get("schema_id") and meta["schema_id"] != schema.id:
        warnings.append(
            f"Schema mismatch: data is from '{meta['schema_id']}', "
            f"current schema is '{schema.id}'. Matching fields will be imported."
        )

    # Extract field values from all groups
    data = {}
    all_field_keys = {f.key for f in schema.all_fields}

    for section_key, section_data in raw.items():
        if section_key == "_meta":
            continue
        if section_key == "additional_information":
            data["_flexible_fields"] = section_data
            continue
        if not isinstance(section_data, dict):
            continue

        for field_key, value in section_data.items():
            if field_key in all_field_keys:
                field_def = schema.get_field(field_key)
                if field_def.is_compound and isinstance(value, dict):
                    # Compound field: deserialize each sub-field
                    compound_data = {}
                    for sf in field_def.sub_fields or []:
                        sv = value.get(sf.key)
                        compound_data[sf.key] = _deserialize_value(sf, sv)
                    data[field_key] = compound_data
                else:
                    data[field_key] = _deserialize_value(field_def, value)
            else:
                warnings.append(f"Skipped unknown field: '{field_key}'")

    return data, warnings


def _deserialize_value(field: FieldDef, value: Any) -> Any:
    """Convert a YAML value back to the expected Python type.
    Returns None for redacted placeholders so they don't overwrite real data."""
    if value is None:
        return None
    # Skip redacted placeholders — don't import them as real data
    if isinstance(value, str) and value.strip() in ("[REDACTED]", REDACTED_TEXT):
        return None
    if field.type == "boolean":
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        return bool(value)
    if field.type == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if field.type == "currency":
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return value
        return value
    return value


# ---------------------------------------------------------------------------
# LLM PROMPT — Generate a schema-aware prompt for LLM assistance
# ---------------------------------------------------------------------------


def generate_llm_prompt(
    schema: Schema,
    existing_data: dict[str, Any] | None = None,
    project_context: str = "",
    redact: bool = True,
) -> str:
    """
    Generate a YAML-based prompt that an LLM can fill in.

    This produces a structured document containing:
      1. Instructions for the LLM
      2. Schema field descriptions with types and constraints
      3. Pre-filled values (if existing_data is provided)
      4. Empty placeholders for fields that need to be filled

    Args:
        schema: The active schema definition.
        existing_data: Optional dict of already-filled values to include.
        project_context: Optional free-text project description to guide the LLM.
        redact: If True (default), fields marked redact=true in the schema
                are masked with [REDACTED]. The LLM sees the field exists
                but doesn't receive the sensitive value. Set to False only
                if you trust the LLM with all data.

    Returns:
        A string designed to be pasted into an LLM chat.
    """
    existing_data = existing_data or {}

    lines = []

    # --- Instructions header ---
    lines.append("# =================================================================")
    lines.append(f"# LLM FILL-IN REQUEST: {schema.name}")
    lines.append("# =================================================================")
    lines.append("#")
    lines.append("# Please fill in the YAML fields below based on the project context")
    lines.append("# and field descriptions. Follow these rules:")
    lines.append("#")
    lines.append("#   1. Replace placeholder values (marked with <...>) with real content")
    lines.append("#   2. Keep the YAML structure exactly as-is — don't rename keys")
    lines.append("#   3. For multiline text, use YAML literal block style (|)")
    lines.append("#   4. For tables, add/remove rows as needed but keep column keys")
    lines.append("#   5. Fields marked REQUIRED must be filled in")
    lines.append("#   6. Fields marked OPTIONAL can be left empty or removed")
    lines.append("#   7. For boolean fields, use true or false")
    lines.append("#   8. For choice fields, pick from the listed options only")
    lines.append("#   9. For date fields, use YYYY-MM-DD format")
    lines.append("#  10. Return ONLY the YAML block between the START/END markers")
    lines.append("#  11. Fields showing [REDACTED] contain sensitive data that was")
    lines.append("#      withheld — do NOT guess or fabricate values for these fields,")
    lines.append("#      just leave them as [REDACTED]")
    lines.append("#")

    if project_context:
        lines.append("# PROJECT CONTEXT:")
        for ctx_line in project_context.strip().splitlines():
            lines.append(f"#   {ctx_line}")
        lines.append("#")

    lines.append("")

    # --- YAML data block ---
    lines.append("# --- START YAML ---")
    lines.append("")

    # Meta
    lines.append("_meta:")
    lines.append(f"  schema_id: {schema.id}")
    lines.append(f"  schema_version: {schema.version}")
    lines.append("  export_type: full_snapshot")
    lines.append(f"  redacted: {str(redact).lower()}")
    lines.append("")

    # Core groups
    for group in schema.core_groups:
        lines.append(f"# --- {group.name} ---")
        lines.append(f"{_group_key(group)}:")
        for field in group.fields:
            lines.extend(_render_field_for_llm(field, existing_data.get(field.key), redact))
        lines.append("")

    # Optional groups
    for group in schema.optional_groups:
        lines.append(f"# --- {group.name} (OPTIONAL) ---")
        lines.append(f"{_group_key(group)}:")
        for field in group.fields:
            lines.extend(_render_field_for_llm(field, existing_data.get(field.key), redact))
        lines.append("")

    # Flexible fields
    lines.append("# --- Additional Information (OPTIONAL) ---")
    lines.append("# Add any project-specific fields not covered above.")
    lines.append("additional_information:")
    flex = existing_data.get("_flexible_fields")
    if flex and isinstance(flex, list):
        for entry in flex:
            lines.append(f"  - field_label: {entry.get('field_label', '')}")
            lines.append(f"    field_value: {entry.get('field_value', '')}")
    else:
        lines.append("  - field_label: <field name>")
        lines.append("    field_value: <value>")

    lines.append("")
    lines.append("# --- END YAML ---")

    return "\n".join(lines)


def _render_field_for_llm(
    field: FieldDef, existing_value: Any = None, redact: bool = False
) -> list[str]:
    """Render a single field as commented YAML lines for LLM consumption."""
    lines = []

    # Build the description comment
    parts = []
    if field.required:
        parts.append("REQUIRED")
    else:
        parts.append("optional")
    parts.append(field.type)
    if field.redact and redact:
        parts.append("REDACTED — do not fill")
    if field.choices:
        parts.append(f"choices: {field.choices}")
    if field.conditional_on:
        parts.append(f"only if {field.conditional_on['field']}={field.conditional_on['value']}")
    if field.placeholder and not (field.redact and redact):
        parts.append(field.placeholder)

    comment = f"  # {field.label} [{', '.join(parts)}]"
    lines.append(comment)

    # If redacted and has existing value, show [REDACTED]
    if redact and field.redact and existing_value is not None:
        lines.append(f"  {field.key}: {REDACTED_TEXT}")
        return lines

    # Render the value based on type
    if field.is_compound:
        lines.extend(_render_compound_for_llm(field, existing_value, redact))
    elif field.is_table:
        lines.extend(_render_table_for_llm(field, existing_value, redact))
    elif existing_value is not None:
        lines.append(f"  {field.key}: {_format_existing_value(field, existing_value)}")
    elif field.default is not None:
        lines.append(f"  {field.key}: {_format_existing_value(field, field.default)}")
    else:
        # Redacted fields with no existing value — show placeholder but mark as redacted
        if redact and field.redact:
            lines.append(f"  {field.key}: {REDACTED_TEXT}")
        else:
            lines.append(f"  {field.key}: <{field.label.lower()}>")

    return lines


def _render_table_for_llm(field: FieldDef, existing_value: Any, redact: bool = False) -> list[str]:
    """Render a table-type field for LLM fill-in, with optional column redaction."""
    lines = []
    lines.append(f"  {field.key}:")

    # Build set of redacted column keys
    redacted_cols = set()
    if redact and field.columns:
        redacted_cols = {col["key"] for col in field.columns if col.get("redact", False)}

    # Use existing data, default rows, or a placeholder row
    rows = existing_value or field.default_rows or []

    if rows:
        for row in rows:
            first = True
            for col in field.columns:
                prefix = "    - " if first else "      "
                val = row.get(col["key"], f"<{col['label'].lower()}>")
                if col["key"] in redacted_cols and val is not None:
                    val = REDACTED_TEXT if col.get("type") not in ("number", "currency") else 0
                lines.append(f"{prefix}{col['key']}: {val}")
                first = False
    else:
        # Generate one placeholder row from column definitions
        first = True
        for col in field.columns:
            prefix = "    - " if first else "      "
            if col["key"] in redacted_cols:
                lines.append(f"{prefix}{col['key']}: {REDACTED_TEXT}")
            else:
                lines.append(f"{prefix}{col['key']}: <{col['label'].lower()}>")
            first = False

    return lines


def _render_compound_for_llm(
    field: FieldDef, existing_value: Any, redact: bool = False
) -> list[str]:
    """Render a compound field with its sub-fields for LLM fill-in."""
    lines = []
    lines.append(f"  {field.key}:")
    existing = existing_value if isinstance(existing_value, dict) else {}

    for sf in field.sub_fields or []:
        # Sub-field comment
        sf_parts = []
        if sf.required:
            sf_parts.append("REQUIRED")
        else:
            sf_parts.append("optional")
        sf_parts.append(sf.type)
        if sf.redact and redact:
            sf_parts.append("REDACTED — do not fill")
        if sf.placeholder and not (sf.redact and redact):
            sf_parts.append(sf.placeholder)

        lines.append(f"    # {sf.label} [{', '.join(sf_parts)}]")

        sv = existing.get(sf.key)

        if redact and sf.redact and sv is not None:
            lines.append(f"    {sf.key}: {REDACTED_TEXT}")
        elif sv is not None:
            lines.append(f"    {sf.key}: {_format_existing_value(sf, sv)}")
        elif sf.default is not None:
            lines.append(f"    {sf.key}: {_format_existing_value(sf, sf.default)}")
        else:
            if redact and sf.redact:
                lines.append(f"    {sf.key}: {REDACTED_TEXT}")
            else:
                lines.append(f"    {sf.key}: <{sf.label.lower()}>")

    return lines


def _format_existing_value(field: FieldDef, value: Any) -> str:
    """Format an existing value for YAML output."""
    if value is None:
        return ""
    if field.type == "boolean":
        return str(bool(value)).lower()
    if field.type == "multiline" and isinstance(value, str) and "\n" in value:
        # Use YAML literal block indicator
        indented = "\n".join(f"    {line}" for line in value.splitlines())
        return f"|\n{indented}"
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


# ---------------------------------------------------------------------------
# LLM SCHEMA REFERENCE — Compact schema description for LLM context
# ---------------------------------------------------------------------------


def generate_schema_reference(schema: Schema) -> str:
    """
    Generate a compact, readable schema reference for sharing with an LLM.

    This is useful when you want the LLM to understand the schema structure
    without sending a full fill-in prompt. The LLM can then answer questions
    about what fields exist, what's required, etc.
    """
    lines = []
    lines.append(f"# Schema Reference: {schema.name}")
    lines.append(f"# ID: {schema.id} | Version: {schema.version}")
    lines.append(
        f"# Total fields: {len(schema.all_fields)} ({len(schema.get_required_fields())} required)"
    )
    lines.append("")

    for group in schema.all_groups:
        tag = "CORE" if group.section == "core" else "OPTIONAL"
        lines.append(f"## [{tag}] {group.name}")
        for f in group.fields:
            req = "✱ " if f.required else "  "
            type_info = f.type
            if f.redact:
                type_info += " 🔒"
            if f.choices:
                type_info += f" → {f.choices}"
            if f.conditional_on:
                type_info += f" (if {f.conditional_on['field']})"
            lines.append(f"  {req}{f.key}: {type_info}")
            if f.placeholder:
                lines.append(f"      hint: {f.placeholder}")
            # Show compound sub-fields
            if f.is_compound and f.sub_fields:
                for sf in f.sub_fields:
                    sreq = "✱ " if sf.required else "  "
                    stype = sf.type
                    if sf.redact:
                        stype += " 🔒"
                    lines.append(f"    {sreq}.{sf.key}: {stype}")
                    if sf.placeholder:
                        lines.append(f"        hint: {sf.placeholder}")
        lines.append("")

    if schema.flexible.enabled:
        lines.append("## [FLEXIBLE] Additional Information")
        lines.append(f"  User-defined key-value pairs (max {schema.flexible.max_entries})")

    return "\n".join(lines)
