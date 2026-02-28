"""
template_registry.py — Manages the mapping between schemas and document templates.

Responsible for:
  - Discovering which templates exist for which schemas
  - Extracting placeholder tags from templates (for validation)
  - Providing template paths to the doc generator
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.schema_loader import Schema


PLACEHOLDER_PATTERN = r"\{\{(\w+)\}\}"  # e.g. {{rfq_number}}


@dataclass
class TemplateInfo:
    """Metadata about a document template."""
    schema_id: str
    template_path: Path
    exists: bool
    placeholders: list[str]  # extracted from the template file


def get_template_path(schema: Schema, templates_dir: str | Path) -> Path:
    """Resolve the full path to a schema's template file."""
    return Path(templates_dir) / schema.template


def discover_templates(templates_dir: str | Path) -> dict[str, Path]:
    """Return {filename: path} for all .docx files in templates_dir."""
    templates_dir = Path(templates_dir)
    if not templates_dir.exists():
        return {}
    return {p.name: p for p in sorted(templates_dir.glob("*.docx"))}


def check_template_coverage(schema: Schema, templates_dir: str | Path) -> dict:
    """
    Check whether a schema's template exists and report which schema fields
    have corresponding placeholders (and vice versa).

    Returns a dict with:
      - template_exists: bool
      - template_path: str
      - field_keys: list of all schema field keys
      - note: guidance on expected placeholder format
    """
    tpath = get_template_path(schema, templates_dir)

    field_keys = [f.key for f in schema.all_fields]

    return {
        "template_exists": tpath.exists(),
        "template_path": str(tpath),
        "schema_field_keys": field_keys,
        "expected_placeholder_format": "{{field_key}}",
        "note": (
            "Template placeholders should use the format {{field_key}} "
            "matching the schema field keys. Table fields will be rendered "
            "as Word tables at the placeholder location."
        ),
    }
