"""
schema_loader.py — Load, validate, and query document schemas.

A schema defines:
  - core_fields: grouped, always present (required or not)
  - optional_fields: grouped, schema-defined but optional
  - flexible_fields: user-defined freeform key-value pairs
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FieldDef:
    """Single field definition from the schema."""
    key: str
    label: str
    type: str  # text, multiline, date, number, currency, choice, boolean, table, compound
    required: bool = False
    placeholder: str = ""
    default: Any = None
    choices: list[str] | None = None
    validation: dict | None = None
    columns: list[dict] | None = None          # for table type
    default_rows: list[dict] | None = None     # for table type
    formula: str | None = None
    conditional_on: dict | None = None         # {"field": ..., "value": ...}
    redact: bool = False                       # if True, value is masked during redacted export
    sub_fields: list['FieldDef'] | None = None  # for compound type — nested named fields

    @property
    def is_table(self) -> bool:
        return self.type == "table"

    @property
    def is_compound(self) -> bool:
        return self.type == "compound"

    @property
    def has_redactable_columns(self) -> bool:
        """For table fields, check if any column is marked redact."""
        if not self.columns:
            return False
        return any(col.get("redact", False) for col in self.columns)

    @property
    def has_redactable_sub_fields(self) -> bool:
        """For compound fields, check if any sub-field is marked redact."""
        if not self.sub_fields:
            return False
        return any(sf.redact for sf in self.sub_fields)


@dataclass
class FieldGroup:
    """A named group of fields (e.g. 'Issuing Organization')."""
    name: str
    fields: list[FieldDef]
    section: str = "core"  # "core", "optional", or "flexible"


@dataclass
class FlexibleFieldsConfig:
    """Configuration for the freeform fields section."""
    enabled: bool = True
    max_entries: int = 20
    label: str = "Additional Information"
    description: str = ""
    columns: list[dict] | None = None


@dataclass
class Schema:
    """Complete document schema."""
    id: str
    name: str
    version: str
    template: str
    description: str
    core_groups: list[FieldGroup]
    optional_groups: list[FieldGroup]
    flexible: FlexibleFieldsConfig

    @property
    def all_groups(self) -> list[FieldGroup]:
        return self.core_groups + self.optional_groups

    @property
    def all_fields(self) -> list[FieldDef]:
        """Flat list of all core + optional fields (not flexible).
        Includes compound fields themselves but NOT their sub_fields,
        since sub_fields are accessed via the parent compound field."""
        return [f for g in self.all_groups for f in g.fields]

    @property
    def all_fields_deep(self) -> list[FieldDef]:
        """Flat list including compound sub-fields (for iteration over every leaf)."""
        result = []
        for f in self.all_fields:
            result.append(f)
            if f.is_compound and f.sub_fields:
                result.extend(f.sub_fields)
        return result

    def get_field(self, key: str) -> FieldDef | None:
        """Look up a field by key. For compound sub-fields, use 'parent.child' notation
        or just the child key (searches sub-fields if top-level not found)."""
        # Direct top-level lookup
        for f in self.all_fields:
            if f.key == key:
                return f
        # Search inside compound fields (flat child key)
        for f in self.all_fields:
            if f.is_compound and f.sub_fields:
                for sf in f.sub_fields:
                    if sf.key == key:
                        return sf
        # Dotted notation: "parent_key.sub_key"
        if "." in key:
            parent_key, sub_key = key.split(".", 1)
            parent = self.get_field(parent_key)
            if parent and parent.is_compound and parent.sub_fields:
                for sf in parent.sub_fields:
                    if sf.key == sub_key:
                        return sf
        return None

    def get_required_fields(self) -> list[FieldDef]:
        """Required fields. For compound fields, the parent is required if any sub-field is."""
        result = []
        for g in self.core_groups:
            for f in g.fields:
                if f.required:
                    result.append(f)
        return result

    def get_table_fields(self) -> list[FieldDef]:
        return [f for f in self.all_fields if f.is_table]

    def get_compound_fields(self) -> list[FieldDef]:
        return [f for f in self.all_fields if f.is_compound]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_field(raw: dict) -> FieldDef:
    """Parse a single field definition from raw YAML dict."""
    # Recursively parse sub-fields for compound type
    sub_fields = None
    if raw.get("type") == "compound" and "fields" in raw:
        sub_fields = [_parse_field(sf) for sf in raw["fields"]]

    return FieldDef(
        key=raw["key"],
        label=raw["label"],
        type=raw["type"],
        required=raw.get("required", False),
        placeholder=raw.get("placeholder", ""),
        default=raw.get("default"),
        choices=raw.get("choices"),
        validation=raw.get("validation"),
        columns=raw.get("columns"),
        default_rows=raw.get("default_rows"),
        formula=raw.get("formula"),
        conditional_on=raw.get("conditional_on"),
        redact=raw.get("redact", False),
        sub_fields=sub_fields,
    )


def _parse_groups(raw_groups: list[dict], section: str) -> list[FieldGroup]:
    """Parse a list of field groups from raw YAML."""
    groups = []
    for g in raw_groups:
        fields = [_parse_field(f) for f in g["fields"]]
        groups.append(FieldGroup(name=g["group"], fields=fields, section=section))
    return groups


def load_schema(path: str | Path) -> Schema:
    """Load and parse a schema YAML file into a Schema object."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")

    with open(path, "r") as f:
        text = f.read()

    return load_schema_from_text(text)


def load_schema_from_text(yaml_text: str) -> Schema:
    """Parse a schema from a YAML string (e.g., fetched from GitHub or pasted)."""
    raw = yaml.safe_load(yaml_text)

    meta = raw["schema"]

    # Core fields
    core_groups = _parse_groups(raw.get("core_fields", []), "core")

    # Optional fields
    optional_groups = _parse_groups(raw.get("optional_fields", []), "optional")

    # Flexible fields config
    flex_raw = raw.get("flexible_fields", {})
    flexible = FlexibleFieldsConfig(
        enabled=flex_raw.get("enabled", True),
        max_entries=flex_raw.get("max_entries", 20),
        label=flex_raw.get("label", "Additional Information"),
        description=flex_raw.get("description", ""),
        columns=flex_raw.get("columns"),
    )

    return Schema(
        id=meta["id"],
        name=meta["name"],
        version=meta["version"],
        template=meta.get("template", ""),
        description=meta.get("description", ""),
        core_groups=core_groups,
        optional_groups=optional_groups,
        flexible=flexible,
    )


# ---------------------------------------------------------------------------
# Discovery — find all schemas in a directory
# ---------------------------------------------------------------------------

def discover_schemas(directory: str | Path) -> dict[str, Path]:
    """Return {schema_id: path} for all .yaml files in directory."""
    directory = Path(directory)
    schemas = {}
    for p in sorted(directory.glob("*.yaml")):
        try:
            with open(p) as f:
                raw = yaml.safe_load(f)
            sid = raw["schema"]["id"]
            schemas[sid] = p
        except (KeyError, yaml.YAMLError):
            continue
    return schemas


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Result of validating user data against a schema."""
    valid: bool
    errors: list[str] = dc_field(default_factory=list)
    warnings: list[str] = dc_field(default_factory=list)


def validate_data(schema: Schema, data: dict[str, Any]) -> ValidationResult:
    """
    Validate a flat dict of {field_key: value} against the schema.
    Tables are expected as list[dict].
    Compound fields are expected as dict[sub_key: value].
    """
    errors = []
    warnings = []

    for f in schema.get_required_fields():
        val = data.get(f.key)
        if f.is_compound:
            # For compound fields, check if the dict exists and has content
            if val is None or not isinstance(val, dict) or not any(val.values()):
                if f.conditional_on:
                    dep_val = data.get(f.conditional_on["field"])
                    if dep_val != f.conditional_on["value"]:
                        continue
                errors.append(f"Missing required field: {f.label} ({f.key})")
            else:
                # Validate required sub-fields within the compound
                for sf in (f.sub_fields or []):
                    if sf.required:
                        sv = val.get(sf.key)
                        if sv is None or (isinstance(sv, str) and sv.strip() == ""):
                            errors.append(
                                f"Missing required sub-field: {f.label} → {sf.label} "
                                f"({f.key}.{sf.key})"
                            )
        elif val is None or (isinstance(val, str) and val.strip() == ""):
            if f.conditional_on:
                dep_val = data.get(f.conditional_on["field"])
                if dep_val != f.conditional_on["value"]:
                    continue
            errors.append(f"Missing required field: {f.label} ({f.key})")

    for f in schema.all_fields:
        val = data.get(f.key)
        if val is None:
            continue

        # Compound field — validate sub-field values
        if f.is_compound and isinstance(val, dict):
            for sf in (f.sub_fields or []):
                sv = val.get(sf.key)
                if sv is None:
                    continue
                _validate_single_field(sf, sv, errors, warnings,
                                       label_prefix=f"{f.label} → ")
            continue

        _validate_single_field(f, val, errors, warnings)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _validate_single_field(
    f: FieldDef, val: Any, errors: list, warnings: list, label_prefix: str = ""
):
    """Validate a single field value against its definition."""
    label = f"{label_prefix}{f.label}"

    if f.type == "date" and isinstance(val, str):
        if not re.match(r"\d{4}-\d{2}-\d{2}", val):
            errors.append(f"{label}: Expected date format YYYY-MM-DD, got '{val}'")

    if f.type == "choice" and f.choices:
        if val not in f.choices:
            warnings.append(f"{label}: '{val}' not in expected choices")

    if f.type == "number":
        try:
            float(val)
        except (TypeError, ValueError):
            errors.append(f"{label}: Expected a number, got '{val}'")

    if f.validation and "pattern" in f.validation:
        if isinstance(val, str) and not re.match(f.validation["pattern"], val):
            errors.append(f"{label}: Value '{val}' doesn't match expected format")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# CLI quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "schemas/rfq_electric_utility.yaml"
    schema = load_schema(path)

    print(f"Schema: {schema.name} (v{schema.version})")
    print(f"Template: {schema.template}")
    print(f"Core groups: {len(schema.core_groups)}")
    print(f"Optional groups: {len(schema.optional_groups)}")
    print(f"Total fields: {len(schema.all_fields)}")
    print(f"Required fields: {len(schema.get_required_fields())}")
    print(f"Table fields: {len(schema.get_table_fields())}")
    print(f"Compound fields: {len(schema.get_compound_fields())}")
    print(f"Flexible fields enabled: {schema.flexible.enabled}")
    print()

    for g in schema.all_groups:
        print(f"[{g.section.upper()}] {g.name}")
        for f in g.fields:
            req = "✱" if f.required else " "
            redact_icon = " 🔒" if f.redact else ""
            cond = f" (if {f.conditional_on['field']})" if f.conditional_on else ""
            print(f"  {req} {f.key}: {f.type}{redact_icon}{cond}")
            if f.is_compound and f.sub_fields:
                for sf in f.sub_fields:
                    sreq = "✱" if sf.required else " "
                    sredact = " 🔒" if sf.redact else ""
                    print(f"      {sreq} .{sf.key}: {sf.type}{sredact}")
        print()
