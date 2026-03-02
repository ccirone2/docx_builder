"""
data_exchange.py — Import/export user data as YAML for reuse.

Two main workflows:
  1. EXPORT: Read data from Excel → serialize to YAML → copy to clipboard
  2. IMPORT: Paste YAML from clipboard → parse → validate → write to Excel

LLM prompt generation lives in llm_helpers.py (split for module size).

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
