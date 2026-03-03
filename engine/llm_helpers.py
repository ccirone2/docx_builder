"""
llm_helpers.py — LLM prompt generation helpers for schema-driven data fill-in.

Two main outputs:
  1. FILL-IN PROMPT: An SCN-based prompt that an LLM can fill in with real data
  2. SCHEMA REFERENCE: A compact schema overview for LLM context

Split from data_exchange.py to keep modules under 400 lines each.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

# Re-export _group_key for LLM prompt generation
from engine.data_exchange import (
    REDACTED_TEXT,
    _group_key,
)
from engine.schema_loader import FieldDef, Schema

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
    Generate an SCN-based prompt that an LLM can fill in.

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

    lines: list[str] = []

    # --- Instructions header ---
    lines.append(";; =================================================================")
    lines.append(f";; LLM FILL-IN REQUEST: {schema.name}")
    lines.append(";; =================================================================")
    lines.append(";;")
    lines.append(";; Please fill in the SCN fields below based on the project context")
    lines.append(";; and field descriptions. Follow these rules:")
    lines.append(";;")
    lines.append(";;   1. Replace placeholder values (marked with <...>) with real content")
    lines.append(";;   2. Keep the SCN structure exactly as-is — don't rename keys")
    lines.append(";;   3. Each key: is followed by its value on the next line")
    lines.append(";;   4. For tables, add/remove +entries as needed but keep column keys")
    lines.append(";;   5. Fields marked REQUIRED must be filled in")
    lines.append(";;   6. Fields marked OPTIONAL can be left empty or removed")
    lines.append(";;   7. For boolean fields, use true or false")
    lines.append(";;   8. For choice fields, pick from the listed options only")
    lines.append(";;   9. For date fields, use YYYY-MM-DD format")
    lines.append(";;  10. Return ONLY the SCN block between the START/END markers")
    lines.append(";;  11. Fields showing [REDACTED] contain sensitive data that was")
    lines.append(";;      withheld — do NOT guess or fabricate values for these fields,")
    lines.append(";;      just leave them as [REDACTED]")
    lines.append(";;")

    if project_context:
        lines.append(";; PROJECT CONTEXT:")
        for ctx_line in project_context.strip().splitlines():
            lines.append(f";;   {ctx_line}")
        lines.append(";;")

    lines.append("")

    # --- SCN data block ---
    lines.append(";; --- START SCN ---")
    lines.append("")

    # Meta
    lines.append("[_meta]")
    lines.append("schema_id:")
    lines.append(schema.id)
    lines.append("schema_version:")
    lines.append(schema.version)
    lines.append("export_type:")
    lines.append("full_snapshot")
    lines.append("redacted:")
    lines.append(str(redact).lower())
    lines.append("")

    # Core groups
    for group in schema.core_groups:
        lines.append(f";; --- {group.name} ---")
        lines.append(f"[{_group_key(group)}]")
        for field in group.fields:
            lines.extend(_render_field_for_llm(field, existing_data.get(field.key), redact))
        lines.append("")

    # Optional groups
    for group in schema.optional_groups:
        lines.append(f";; --- {group.name} (OPTIONAL) ---")
        lines.append(f"[{_group_key(group)}]")
        for field in group.fields:
            lines.extend(_render_field_for_llm(field, existing_data.get(field.key), redact))
        lines.append("")

    # Flexible fields
    lines.append(";; --- Additional Information (OPTIONAL) ---")
    lines.append(";; Add any project-specific fields not covered above.")
    flex = existing_data.get("_flexible_fields")
    if flex and isinstance(flex, list):
        for entry in flex:
            lines.append("+additional_information")
            lines.append("field_label:")
            lines.append(entry.get("field_label", ""))
            lines.append("field_value:")
            lines.append(entry.get("field_value", ""))
    else:
        lines.append("+additional_information")
        lines.append("field_label:")
        lines.append("<field name>")
        lines.append("field_value:")
        lines.append("<value>")

    lines.append("")
    lines.append(";; --- END SCN ---")

    return "\n".join(lines)


def _render_field_for_llm(
    field: FieldDef, existing_value: Any = None, redact: bool = False
) -> list[str]:
    """Render a single field as SCN lines with comment annotations for LLM consumption."""
    lines: list[str] = []

    # Build the description comment
    parts: list[str] = []
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

    comment = f";; {field.label} [{', '.join(parts)}]"
    lines.append(comment)

    # If redacted and has existing value, show [REDACTED]
    if redact and field.redact and existing_value is not None:
        lines.append(f"{field.key}:")
        lines.append(REDACTED_TEXT)
        return lines

    # Render the value based on type
    if field.is_compound:
        lines.extend(_render_compound_for_llm(field, existing_value, redact))
    elif field.is_table:
        lines.extend(_render_table_for_llm(field, existing_value, redact))
    elif existing_value is not None:
        lines.append(f"{field.key}:")
        lines.append(_format_existing_value(field, existing_value))
    elif field.default is not None:
        lines.append(f"{field.key}:")
        lines.append(_format_existing_value(field, field.default))
    else:
        # Redacted fields with no existing value — show placeholder but mark as redacted
        if redact and field.redact:
            lines.append(f"{field.key}:")
            lines.append(REDACTED_TEXT)
        else:
            lines.append(f"{field.key}:")
            lines.append(f"<{field.label.lower()}>")

    return lines


def _render_table_for_llm(field: FieldDef, existing_value: Any, redact: bool = False) -> list[str]:
    """Render a table-type field for LLM fill-in using SCN +entry notation."""
    lines: list[str] = []

    # Build set of redacted column keys
    redacted_cols: set[str] = set()
    if redact and field.columns:
        redacted_cols = {col["key"] for col in field.columns if col.get("redact", False)}

    # Use existing data, default rows, or a placeholder row
    rows = existing_value or field.default_rows or []

    if rows:
        for row in rows:
            lines.append(f"+{field.key}")
            for col in field.columns:
                val = row.get(col["key"], f"<{col['label'].lower()}>")
                if col["key"] in redacted_cols and val is not None:
                    val = REDACTED_TEXT if col.get("type") not in ("number", "currency") else "0"
                lines.append(f"{col['key']}:")
                lines.append(str(val) if val is not None else "")
    else:
        # Generate one placeholder row from column definitions
        lines.append(f"+{field.key}")
        for col in field.columns:
            lines.append(f"{col['key']}:")
            if col["key"] in redacted_cols:
                lines.append(REDACTED_TEXT)
            else:
                lines.append(f"<{col['label'].lower()}>")

    return lines


def _render_compound_for_llm(
    field: FieldDef, existing_value: Any, redact: bool = False
) -> list[str]:
    """Render a compound field with its sub-fields using dot-notation keys."""
    lines: list[str] = []
    existing = existing_value if isinstance(existing_value, dict) else {}

    for sf in field.sub_fields or []:
        # Sub-field comment
        sf_parts: list[str] = []
        if sf.required:
            sf_parts.append("REQUIRED")
        else:
            sf_parts.append("optional")
        sf_parts.append(sf.type)
        if sf.redact and redact:
            sf_parts.append("REDACTED — do not fill")
        if sf.placeholder and not (sf.redact and redact):
            sf_parts.append(sf.placeholder)

        lines.append(f";; {sf.label} [{', '.join(sf_parts)}]")

        sv = existing.get(sf.key)

        if redact and sf.redact and sv is not None:
            lines.append(f"{field.key}.{sf.key}:")
            lines.append(REDACTED_TEXT)
        elif sv is not None:
            lines.append(f"{field.key}.{sf.key}:")
            lines.append(_format_existing_value(sf, sv))
        elif sf.default is not None:
            lines.append(f"{field.key}.{sf.key}:")
            lines.append(_format_existing_value(sf, sf.default))
        else:
            if redact and sf.redact:
                lines.append(f"{field.key}.{sf.key}:")
                lines.append(REDACTED_TEXT)
            else:
                lines.append(f"{field.key}.{sf.key}:")
                lines.append(f"<{sf.label.lower()}>")

    return lines


def _format_existing_value(field: FieldDef, value: Any) -> str:
    """Format an existing value for SCN output."""
    if value is None:
        return ""
    if field.type == "boolean":
        return str(bool(value)).lower()
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
    lines: list[str] = []
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
